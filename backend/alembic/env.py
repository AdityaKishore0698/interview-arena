import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.base import Base
from app.core.config import settings


def get_url() -> str:
    """Resolve the database URL used for migrations.

    Prefers ``DIRECT_URL`` — a direct, non-pooled connection. Pooled
    connections (e.g. PgBouncer / Supabase pooler in transaction mode) break
    Alembic's DDL, advisory locks and prepared statements, so migrations must
    bypass the pool. Falls back to ``DATABASE_URL`` when ``DIRECT_URL`` is not
    set, then to the app settings default so local development still works with
    no environment variables configured.
    """
    url = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL") or settings.DATABASE_URL
    # This env.py runs migrations through an async engine, so a bare postgres
    # scheme (which hosted providers hand out) must be given an async driver.
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


config = context.config
config.set_main_option("sqlalchemy.url", get_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
