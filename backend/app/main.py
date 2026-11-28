from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import time
import re

from .core.config import settings
from .core.logger import get_logger
from .core.database import async_session, engine
from .core.dependencies import OPERATOR_ROLES
from .core.exceptions import register_exception_handlers
from .core.security import decode_token
from .core.ws_manager import ws_manager
from .api.v1 import router as api_v1
from .services.auth_service import AuthService

logger = get_logger("app.main")


class RequestTimingMiddleware:
    """Log request timing at response delivery without logging request contents."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = time.perf_counter()
        method = scope.get("method", "?")
        path = scope.get("path", "?")
        endpoint = re.sub(r"/[0-9a-fA-F-]{36}(?=/|$)", "/{id}", path)
        logger.info("HTTP request start method=%s endpoint=%s", method, endpoint)
        status_code = 500
        response_logged = False

        async def timed_send(message):
            nonlocal status_code, response_logged
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
            if (
                message["type"] == "http.response.body"
                and not message.get("more_body", False)
                and not response_logged
            ):
                response_logged = True
                logger.info(
                    "HTTP response method=%s endpoint=%s status=%d elapsed_ms=%.1f",
                    method,
                    endpoint,
                    status_code,
                    (time.perf_counter() - started_at) * 1000,
                )

        try:
            await self.app(scope, receive, timed_send)
        except Exception as exc:
            if not response_logged:
                logger.error(
                    "HTTP request failed method=%s endpoint=%s error_type=%s elapsed_ms=%.1f",
                    method,
                    endpoint,
                    type(exc).__name__,
                    (time.perf_counter() - started_at) * 1000,
                )
            raise

app = FastAPI(
    title="EmergencyIQ API",
    version="1.0.0",
    description=(
        "AI-Powered Emergency Dispatch Platform. "
        "Versioned under /api/v1 — additive fields are safe; clients should ignore unknown keys."
    ),
)
app.add_middleware(RequestTimingMiddleware)

register_exception_handlers(app)

# Strict CORS allowlist from env (dashboard origin only; no wildcard)
_cors_origins = [o for o in (settings.ALLOWED_ORIGINS or []) if o != "*"]
if not _cors_origins:
    _cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1.api_router, prefix="/api/v1")


@app.websocket("/ws/operator")
async def operator_websocket(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    raw_token = token
    if not raw_token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            raw_token = auth_header[7:].strip()

    if not raw_token:
        await websocket.close(code=1008)
        return

    try:
        payload = decode_token(raw_token)
        if not payload or payload.get("type") != "access":
            await websocket.close(code=1008)
            return
        async with async_session() as db:
            user = await AuthService.get_user_by_id(db, str(payload.get("sub")))
            if not user or not user.is_active or (user.role_name or "").lower() not in OPERATOR_ROLES:
                await websocket.close(code=1008)
                return
    except Exception:
        await websocket.close(code=1008)
        return

    await ws_manager.connect("operator", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect("operator", websocket)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "api_version": "v1",
        "docs": "/docs",
        "health": "/api/v1/health",
        "emergency_calls": "/api/v1/emergency-calls",
    }

@app.on_event("startup")
async def startup_event():
    start = time.time()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as exc:
        logger.exception("Database connection failed: %s", exc)
    elapsed = time.time() - start
    logger.info("Startup complete in %.2f seconds", elapsed)
    logger.info("Audio detector backend: %s", settings.AUDIO_EVENT_DETECTOR_BACKEND)
    logger.info("Ollama model: %s", settings.OLLAMA_MODEL)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down gracefully")
