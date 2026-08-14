
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from app.core.config import settings


# Async engine and sessionmaker using asyncpg
DATABASE_URL = settings.DATABASE_URL

async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    future=True,
    echo=False,
)

async_session = async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an AsyncSession."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()