"""
Script to create a test API key for development.
"""
import asyncio
import secrets
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.api_key import APIKey

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_test_api_key():
    """Create a test API key for development."""
    # Generate a random API key
    plain_key = secrets.token_urlsafe(32)
    
    # Hash it
    hashed_key = pwd_context.hash(plain_key)
    
    # Create database connection
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Create API key
        api_key = APIKey(
            key=hashed_key,
            name="Test Development Key",
            role="admin",
            is_active=True
        )
        session.add(api_key)
        await session.commit()
        
        print("=" * 60)
        print("✅ Test API Key Created Successfully!")
        print("=" * 60)
        print(f"API Key: {plain_key}")
        print(f"Name: Test Development Key")
        print(f"Role: admin")
        print("=" * 60)
        print("⚠️  SAVE THIS KEY! It won't be shown again.")
        print("=" * 60)
        print("\nUse it in your requests like this:")
        print(f"\ncurl -X 'GET' \\")
        print(f"  'http://127.0.0.1:8000/v1/current?location=Accra' \\")
        print(f"  -H 'accept: application/json' \\")
        print(f"  -H 'X-API-Key: {plain_key}'")
        print("=" * 60)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_api_key())