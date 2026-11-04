"""
Alembic environment.

Two ways in:
  * Server startup (app.core.init_db.run_migrations) passes an open connection
    through config.attributes["connection"]; migrations run on it.
  * CLI (`alembic upgrade head`) builds an async engine from settings.DATABASE_URL.
"""
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.models import Base  # registers every model on Base.metadata

target_metadata = Base.metadata


def _configure_and_run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",  # SQLite needs batch ALTERs
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_offline() -> None:
    context.configure(url=settings.DATABASE_URL, target_metadata=target_metadata,
                      literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        await conn.run_sync(_configure_and_run)
        await conn.commit()
    await engine.dispose()


def run_online() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _configure_and_run(connection)
    else:
        asyncio.run(_run_async())


if context.is_offline_mode():
    run_offline()
else:
    run_online()
