"""
Seed script for API keys.

This script creates a default development API key for initial testing.

Run this script after running database migrations:
    python -m scripts.seed_api_keys
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.crud.api_key import api_key as api_key_crud
from app.utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def seed_api_keys():
    """Seed the database with a default development API key."""
    
    # Create async engine
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=False,
    )

    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    logger.info("=" * 60)
    logger.info("Starting API key seeding process")
    logger.info("=" * 60)

    async with async_session() as session:
        try:
            # Check if development key already exists
            existing_key = await api_key_crud.get_by_name(session, name="Development Key")
            
            if existing_key:
                logger.warning("Development Key already exists, skipping creation...")
                logger.info("=" * 60)
                logger.info("Use the API key creation endpoint to generate new keys:")
                logger.info("  POST /api/v1/api-keys/")
                logger.info("=" * 60)
            else:
                # Create development API key
                api_key_obj, plain_key = await api_key_crud.create(
                    session,
                    name="Development Key",
                    role="read_only",
                    is_active=True
                )

                logger.info("=" * 60)
                logger.info("✓ Development API Key created successfully!")
                logger.info("=" * 60)
                logger.warning("⚠️  IMPORTANT: Store this key securely - it will not be shown again!")
                logger.info("=" * 60)
                logger.info(f"API Key: {plain_key}")
                logger.info("=" * 60)
                logger.info("Use this key in the X-API-Key header:")
                logger.info("  curl -H 'X-API-Key: <your-key>' http://localhost:8000/api/v1/...")
                logger.info("=" * 60)

        except Exception as e:
            await session.rollback()
            logger.error(f"✗ Error during seeding: {e}")
            raise
        finally:
            await engine.dispose()


def main():
    """Main entry point for the seed script."""
    try:
        asyncio.run(seed_api_keys())
        logger.info("\n🎉 API key seeding completed!")

    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Seeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
