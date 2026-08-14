from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import time

import app.models  # ensure model modules are imported for metadata

from app.core.config import settings
from app.core.logger import get_logger
from app.api.v1.router import api_router
from app.core.exceptions import register_exception_handlers
from app.core.database import async_engine

logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="EmergencyIQ API",
        version="1.0.0",
        description="AI-Powered Emergency Dispatch Platform",
    )

    # Ensure CORS gets a list of origins (settings.allowed_origins property)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(api_router, prefix="/api/v1")

    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting EmergencyIQ API...")
        start = time.time()

        try:
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connected successfully")
        except Exception as exc:
            logger.exception("Database connectivity failed: %s", exc)

        logger.info("Audio detector backend: %s", settings.AUDIO_EVENT_DETECTOR_BACKEND)
        logger.info("Ollama model: %s", settings.OLLAMA_MODEL)
        logger.info("Boot time: %.3fs", time.time() - start)

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down EmergencyIQ API gracefully")

    @app.get("/")
    async def root():
        return {"message": "EmergencyIQ API Running", "status": "success"}

    return app


app = create_app()