"""Test creating a new API key and immediately verifying it."""
import asyncio
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import secrets

DB = "postgresql+asyncpg://gmet_weather_6nsz_user:JVLHyY3wOV4k45yH7cxwMEoyfRhhOUlD@dpg-d5feauje5dus73bemddg-a/gmet_weather_6nsz"

async def test():
    engine = create_async_engine(DB)

    # Generate a new key
    plain_key = secrets.token_hex(16)
    print(f"Generated plain key: {plain_key}")
    print(f"Plain key length: {len(plain_key)}")

    # Hash it
    hashed = bcrypt.hashpw(plain_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    print(f"\nHashed key: {hashed}")
    print(f"Hash length: {len(hashed)}")

    # Verify locally before inserting
    local_verify = bcrypt.checkpw(plain_key.encode('utf-8'), hashed.encode('utf-8'))
    print(f"\nLocal verification BEFORE insert: {local_verify}")

    async with engine.connect() as conn:
        # Insert the key
        await conn.execute(text(
            "INSERT INTO api_keys (key, name, role, is_active) VALUES (:key, :name, :role, :is_active)"
        ), {"key": hashed, "name": "Test Key - Direct Insert", "role": "admin", "is_active": True})
        await conn.commit()
        print("\nInserted key into database")

        # Retrieve and verify
        result = await conn.execute(text(
            "SELECT key FROM api_keys WHERE name = 'Test Key - Direct Insert' ORDER BY id DESC LIMIT 1"
        ))
        row = result.fetchone()

        if row:
            db_hash = row[0]
            print(f"\nRetrieved hash from DB: {db_hash}")
            print(f"DB hash length: {len(db_hash)}")
            print(f"Hashes match: {hashed == db_hash}")

            # Verify from DB
            db_verify = bcrypt.checkpw(plain_key.encode('utf-8'), db_hash.encode('utf-8'))
            print(f"\nVerification from DB: {db_verify}")

            if db_verify:
                print(f"\n{'='*60}")
                print("SUCCESS! Use this API key:")
                print(f"  {plain_key}")
                print(f"{'='*60}")
            else:
                print("\nFAILED: Key verification failed after retrieval from DB")
                print(f"  Original hash: {hashed}")
                print(f"  DB hash:       {db_hash}")
        else:
            print("ERROR: Could not retrieve inserted key")

asyncio.run(test())
