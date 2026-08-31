from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from ...core.config import settings
from ...core.database import engine

router = APIRouter()

@router.get("", summary="Service health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}

@router.get("/db", summary="Database health")
async def health_db():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except SQLAlchemyError:
        return {"status": "error", "db": "unavailable"}
