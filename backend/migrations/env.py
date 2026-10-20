"""Окружение Alembic: URL базы и метаданные моделей берутся из приложения."""
from logging.config import fileConfig

from alembic import context

import app.models  # noqa: F401  регистрирует все таблицы в Base.metadata
from app.core.config import settings
from app.core.db import Base, make_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
# SQLite не умеет ALTER COLUMN — для него Alembic пересоздаёт таблицу (batch mode)
RENDER_AS_BATCH = settings.is_sqlite


def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"},
                      render_as_batch=RENDER_AS_BATCH)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = make_engine(settings.database_url)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=RENDER_AS_BATCH)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
