import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def test():
    engine = create_async_engine(settings.DATABASE_URL)

    async with engine.connect() as conn:
        result = await conn.execute("SELECT 1")
        print(result)

    await engine.dispose()

asyncio.run(test())