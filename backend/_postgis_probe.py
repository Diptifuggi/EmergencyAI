import asyncio

from sqlalchemy import text

from app.core.database import engine


async def main() -> None:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT name, default_version, installed_version "
                "FROM pg_available_extensions WHERE name = 'postgis'"
            )
        )
        row = result.mappings().one_or_none()
        print(dict(row) if row else "postgis unavailable")
    await engine.dispose()


asyncio.run(main())
