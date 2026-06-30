import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.config import settings
from app.database import Base
import app.models

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

VERSION_TABLE = "alembic_version_activity_consumer"

# Таблицы, которыми владеет этот сервис. Alembic будет учитывать
# только их при autogenerate и игнорировать всё остальное в базе
# (таблицы users/todos/categories/refresh_tokens принадлежат todo_app).
OWNED_TABLES = {"activity_log"}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in OWNED_TABLES
    # для колонок/индексов/constraint'ов проверяем таблицу, к которой они относятся
    if hasattr(object, "table") and object.table is not None:
        return object.table.name in OWNED_TABLES
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table=VERSION_TABLE,
        include_object=include_object,
    )
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