"""
Alembic environment configuration.

This file contains the configuration for Alembic migrations,
including database connection and metadata setup.
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the parent directory to the path so we can import the app module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import Base without triggering async engine creation
# We need to import models first, then get Base
from app.config import settings

# Import all models to ensure they are registered with Base.metadata
from app.models.user import User
from app.models.api_key import APIKey
from app.models.station import Station
from app.models.synoptic_observation import SynopticObservation
from app.models.daily_summary import DailySummary

# Import Base after models (this will still trigger engine creation, but we'll work around it)
# For SQLite migrations, we'll use a sync engine from alembic config instead
from sqlalchemy.orm import declarative_base
Base = declarative_base()

# Import metadata from models
from app.models.base import BaseModel
# Copy metadata from the actual Base
import app.database as db_module
Base.metadata = db_module.Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here, too.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = settings.SQLALCHEMY_DATABASE_URI
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations with a database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    # Prefer environment variable DATABASE_URL (Railway/Render) or settings
    # Fall back to alembic.ini only for local SQLite development
    url = os.getenv('DATABASE_URL')

    if not url:
        # Use settings.SQLALCHEMY_DATABASE_URI constructed from individual env vars
        try:
            url = settings.SQLALCHEMY_DATABASE_URI
        except Exception as e:
            raise RuntimeError(
                f"Failed to construct database URL: {e}\n"
                "Ensure POSTGRES_SERVER, POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB are set"
            )

    # Validate URL was successfully obtained
    if not url or url == "None":
        raise RuntimeError(
            "No database URL configured. "
            "Set DATABASE_URL or individual Postgres environment variables"
        )

    # Convert async drivers to sync drivers for migrations
    if url.startswith('postgresql+asyncpg://'):
        # Async driver → sync driver for migrations
        url = url.replace('postgresql+asyncpg://', 'postgresql://')
    elif url.startswith('postgres://'):
        # Railway format → standard PostgreSQL format
        url = url.replace('postgres://', 'postgresql://')
    elif url.startswith('sqlite+aiosqlite://'):
        # Async SQLite → sync SQLite for migrations
        url = url.replace('sqlite+aiosqlite://', 'sqlite://')

    # Override alembic.ini URL with environment-based URL
    config.set_main_option("sqlalchemy.url", url)

    # Use sync engine for migrations
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
