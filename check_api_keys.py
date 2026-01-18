"""Check API keys in database."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB = "postgresql+asyncpg://gmet_weather_6nsz_user:JVLHyY3wOV4k45yH7cxwMEoyfRhhOUlD@dpg-d5feauje5dus73bemddg-a/gmet_weather_6nsz"

async def check():
    engine = create_async_engine(DB)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, name, is_active FROM api_keys"))
        rows = result.fetchall()
        print("API Keys in database:")
        for row in rows:
            print(f"  ID: {row[0]}, Name: {row[1]}, Active: {row[2]}")
        if not rows:
            print("  (none found)")

asyncio.run(check())
