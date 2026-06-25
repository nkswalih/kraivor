import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.infrastructure.db.base import Base

# Import all models so Base.metadata is populated
import app.infrastructure.db.models.analysis_job  # noqa: F401
import app.infrastructure.db.models.finding  # noqa: F401
import app.infrastructure.db.models.dead_code  # noqa: F401
import app.infrastructure.db.models.error_finding  # noqa: F401
import app.infrastructure.db.models.performance_metric  # noqa: F401
import app.infrastructure.db.models.simulation_result  # noqa: F401
import app.infrastructure.db.models.score_history  # noqa: F401
import app.infrastructure.db.models.enterprise_guide  # noqa: F401
import app.infrastructure.db.models.file_analysis  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database.url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, version_table_schema="analysis")
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
