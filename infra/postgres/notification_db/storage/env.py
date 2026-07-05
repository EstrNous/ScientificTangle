import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from config import NotificationDbSettings
from models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = NotificationDbSettings()
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def configure_context(**values: object) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,
        version_table="alembic_version_notification",
        **values,
    )


def run_migrations_offline() -> None:
    configure_context(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    configure_context(connection=connection)
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
    asyncio.run(run_migrations_online())
