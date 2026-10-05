import logging  # noqa: F401
from logging.config import fileConfig

from alembic import context
from sqlmodel import SQLModel

from src.core.config import settings  # noqa: F401
from src.core.database import engine

import src.catalog.models  # noqa: F401
import src.hydration.models  # noqa: F401
import src.users.models  # noqa: F401

context_config = context.config
if context_config.config_file_name is not None:
    fileConfig(context_config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_env():
    run_migrations_offline()
else:
    run_migrations_online()
