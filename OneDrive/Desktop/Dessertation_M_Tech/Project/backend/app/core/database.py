from __future__ import annotations

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
from .config import settings

DATABASE_URL = settings.DATABASE_URL

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
