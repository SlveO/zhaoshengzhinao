import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Alembic Config object
config = context.config

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use DATABASE_URL from environment, falling back to alembic.ini
database_url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))

# Import all models so Base.metadata is populated
from models import Base  # noqa: E402
from models import college, admission, user, profile, recommendation, industry, mapping, recommendation_feedback  # noqa: E402, F401
from tenants.models import Tenant, TenantUser, TenantData, Department, SessionProfile  # noqa: E402, F401

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run migrations in 'online' mode with async engine."""
    connectable = create_async_engine(database_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    """Run async migrations."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
