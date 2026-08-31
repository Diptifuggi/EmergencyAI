from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context
from pathlib import Path

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ensure the backend package is importable (assumes this file lives in backend/alembic)
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# import the app's metadata
from app.core.database import engine, Base
import app.models  # noqa: F401 - register all ORM models with Base.metadata

target_metadata = Base.metadata


async def run_migrations_online() -> None:
    connectable: AsyncEngine = engine

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations() -> None:
    asyncio.run(run_migrations_online())


if context.is_offline_mode():
    raise RuntimeError("Offline mode not supported by this template")
else:
    run_migrations()
