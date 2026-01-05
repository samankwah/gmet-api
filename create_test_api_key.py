import asyncio
import secrets
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.api_key import APIKey


async def create_test_api_key():
    """Create a test API key for development."""
    # Generate a simple API key
    plain_key = secrets.token_urlsafe(24)
    
    # Hash it using bcrypt directly
    hashed_key = bcrypt.hashpw(plain_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        api_key = APIKey(
            key=hashed_key,
            name="Test Development Key",
            role="admin",
            is_active=True
        )
        session.add(api_key)
        await session.commit()
        
        print("=" * 70)
        print(" Test API Key Created Successfully!")
        print("=" * 70)
        print(f"API Key: {plain_key}")
        print(f"Name: Test Development Key")
        print(f"Role: admin")
        print("=" * 70)
        print("  SAVE THIS KEY! It won't be shown again.")
        print("=" * 70)
        print("\nUse it in your requests:")
        print("\nCURL example:")
        print(f"curl -X GET \"http://127.0.0.1:8000/v1/current?location=Accra\" ^")
        print(f"  -H \"accept: application/json\" ^")
        print(f"  -H \"X-API-Key: {plain_key}\"")
        print("\nOr in Swagger UI (http://127.0.0.1:8000/docs):")
        print("  1. Click the 'Authorize' button")
        print(f"  2. Enter: {plain_key}")
        print("  3. Click 'Authorize'")
        print("=" * 70)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_api_key())
