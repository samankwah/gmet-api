"""Generate a new API key for testing."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import get_db
from app.models.api_key import APIKey
from app.utils.security import get_password_hash, generate_api_key
from datetime import datetime, timezone


async def create_new_key():
    """Create a new API key."""
    async for db in get_db():
        # Generate new API key
        plain_key = generate_api_key()
        hashed_key = get_password_hash(plain_key)

        api_key = APIKey(
            key=hashed_key,
            name=f"Testing Key {datetime.now().strftime('%Y%m%d%H%M%S')}",
            role="user",
            is_active=True,
            last_used_at=datetime.now(timezone.utc)
        )
        db.add(api_key)
        await db.commit()

        print("\n" + "="*70)
        print("NEW API KEY GENERATED!")
        print("="*70)
        print(f"\nAPI KEY: {plain_key}")
        print(f"\nName: {api_key.name}")
        print(f"Role: {api_key.role}")
        print("\n" + "="*70)
        print("\nUse this in Swagger UI:")
        print("1. Click the 'Authorize' button")
        print("2. Enter the API key above in the X-API-Key field")
        print("3. Click 'Authorize'")
        print("="*70 + "\n")
        break


if __name__ == "__main__":
    asyncio.run(create_new_key())
