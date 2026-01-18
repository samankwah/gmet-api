"""Debug authentication issue."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB = "postgresql+asyncpg://gmet_weather_6nsz_user:JVLHyY3wOV4k45yH7cxwMEoyfRhhOUlD@dpg-d5feauje5dus73bemddg-a/gmet_weather_6nsz"

async def debug():
    engine = create_async_engine(DB)
    async with engine.connect() as conn:
        # Get full API key details - using correct column name 'key'
        result = await conn.execute(text(
            "SELECT id, name, key, role, is_active FROM api_keys LIMIT 1"
        ))
        row = result.fetchone()

        if row:
            print(f"ID: {row[0]}")
            print(f"Name: {row[1]}")
            key_val = row[2]
            print(f"Key (hash): {key_val[:60] if key_val else 'None'}...")
            print(f"Key length: {len(key_val) if key_val else 0}")
            print(f"Role: {row[3]}")
            print(f"Is Active: {row[4]}")

            # Check hash format
            if key_val:
                print(f"\nHash analysis:")
                print(f"  Starts with $2b$: {key_val.startswith('$2b$')}")
                print(f"  Starts with $2a$: {key_val.startswith('$2a$')}")

                # Check if it looks like a valid bcrypt hash
                is_valid_bcrypt = (
                    len(key_val) == 60 and
                    (key_val.startswith('$2b$') or key_val.startswith('$2a$'))
                )
                print(f"  Looks like valid bcrypt: {is_valid_bcrypt}")
        else:
            print("No API keys found")

asyncio.run(debug())
