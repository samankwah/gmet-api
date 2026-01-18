"""
Database configuration and session management.

This module contains SQLAlchemy engine, session configuration,
and database table creation utilities.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

# Configure database URL based on environment
database_url = settings.SQLALCHEMY_DATABASE_URI
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
# SQLite URLs are now properly formatted in config.py

# Create async engine
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    future=True,
    poolclass=StaticPool if settings.DEBUG else None,
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for all database models
Base = declarative_base()


_models_configured = False


def _configure_models():
    """Import all models to ensure SQLAlchemy mappers are properly configured."""
    global _models_configured
    if _models_configured:
        return
    # This must be done before any database queries to resolve relationships
    import app.models  # noqa: F401
    # Explicitly configure all mappers to resolve relationships
    from sqlalchemy.orm import configure_mappers
    configure_mappers()
    _models_configured = True


async def get_db() -> AsyncSession:
    """
    Dependency function to get database session.

    Yields an async database session and ensures proper cleanup.
    """
    # Ensure models are configured before any database access
    _configure_models()

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """
    Create all database tables.

    This function should be called during application startup.
    """
    async with engine.begin() as conn:
        # Import all models to ensure they are registered with Base
        from app.models import user, weather_data  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """
    Drop all database tables.

    WARNING: This will delete all data. Use with caution.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
