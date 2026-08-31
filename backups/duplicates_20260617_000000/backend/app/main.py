from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import asyncio
import app.models
from app.core.config import settings
from app.core.logger import get_logger
from app.api.v1.router import api_router
from app.core.exceptions import register_exception_handlers
from app.core.database import async_engine
from app.api.health import router as health_router


logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.0")

    origins = settings.ALLOWED_ORIGINS or ["http://localhost:5173", "http://localhost:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    register_exception_handlers(app)

    @app.on_event("startup")
    async def startup_event() -> None:
        logger.info("Starting EmergencyIQ API — testing database connectivity...")
        try:
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connectivity OK")
        except Exception as exc:  # noqa: BLE001 - we want to catch any startup failure and log
            logger.exception("Database connectivity failed on startup: %s", exc)

    return app


app = create_app()
app.include_router(health_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
