"""
Script to create an admin API key for initial setup.

Run this after deploying to production to create the first admin API key.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.crud.api_key import api_key as api_key_crud


async def create_admin_key():
    """Create an admin API key."""
    print("=" * 80)
    print("GMet Weather API - Admin Key Creation")
    print("=" * 80)
    print(f"\nConnecting to database: {settings.POSTGRES_DB}")

    # Create async engine
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=False,
        pool_pre_ping=True
    )

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as db:
        print("\nCreating admin API key...")

        # Create admin key
        api_key_obj, plain_key = await api_key_crud.create(
            db,
            name="Admin Access - CTO",
            role="admin",
            is_active=True
        )

        await db.commit()

        print("\n" + "=" * 80)
        print("✅ ADMIN API KEY CREATED SUCCESSFULLY!")
        print("=" * 80)
        print(f"\nKey ID: {api_key_obj.id}")
        print(f"Name: {api_key_obj.name}")
        print(f"Role: {api_key_obj.role}")
        print(f"\n🔑 API KEY (save this - shown only once):")
        print(f"\n    {plain_key}")
        print("\n" + "=" * 80)
        print("\n⚠️  IMPORTANT: Copy this key now! It will not be shown again.")
        print("\nUsage:")
        print(f"  curl -H 'X-API-Key: {plain_key}' https://your-api.com/api/v1/...")
        print("=" * 80 + "\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin_key())
