"""
Quick script to create the first admin API key.
Run: python create_first_key.py
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Render internal database (use this when running in Render Shell)
RENDER_DB = {
    "user": "gmet_weather_6nsz_user",
    "password": "JVLHyY3wOV4k45yH7cxwMEoyfRhhOUlD",
    "host": "dpg-d5feauje5dus73bemddg-a",
    "db": "gmet_weather_6nsz"
}

# Try DATABASE_URL first, fall back to hardcoded Render credentials
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("No DATABASE_URL found, using Render internal database...")
    DATABASE_URL = f"postgresql://{RENDER_DB['user']}:{RENDER_DB['password']}@{RENDER_DB['host']}/{RENDER_DB['db']}"

# Convert to async driver if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

print(f"Connecting to database...")

async def create_key():
    from app.crud.api_key import api_key as api_key_crud

    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("Creating admin API key...")
        api_key_obj, plain_key = await api_key_crud.create(
            db,
            name="Admin Access - Initial Setup",
            role="admin",
            is_active=True
        )
        await db.commit()

        print("\n" + "=" * 80)
        print("✅ ADMIN API KEY CREATED!")
        print("=" * 80)
        print(f"\n🔑 API KEY: {plain_key}")
        print("\n⚠️  Save this key! It won't be shown again.")
        print("\nTest with:")
        print(f"curl -H 'X-API-Key: {plain_key}' https://met-api-zrsh.onrender.com/api/v1/stations")
        print("=" * 80 + "\n")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_key())
