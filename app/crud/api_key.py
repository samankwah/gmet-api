"""
API Key CRUD operations.

This module contains CRUD operations specific to API key management.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.models.api_key import APIKey
from app.core.security import hash_api_key, verify_api_key, generate_api_key_plaintext


class CRUDAPIKey(CRUDBase[APIKey, dict, dict]):
    """
    CRUD operations for APIKey model.
    """

    async def create(
        self,
        db: AsyncSession,
        *,
        name: str,
        role: str = "read_only",
        is_active: bool = True
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.

        Generates a plain text key, hashes it, and stores only the hash.
        Returns both the APIKey object and the plain text key (shown only once).

        Args:
            db: Database session
            name: Descriptive name for the key
            role: Key role ('admin', 'read_only', or 'partner')
            is_active: Whether the key is active

        Returns:
            Tuple of (APIKey instance, plain_text_key)
        """
        # Generate plain text key
        plain_key = generate_api_key_plaintext()
        # Hash the key
        hashed_key = hash_api_key(plain_key)

        # Create database object
        db_obj = APIKey(
            key=hashed_key,
            name=name,
            role=role,
            is_active=is_active
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj, plain_key

    async def get_by_hashed_key(
        self,
        db: AsyncSession,
        *,
        hashed_key: str
    ) -> Optional[APIKey]:
        """
        Get API key by hashed key value.

        Note: This is primarily for internal use. Use verify_and_get instead.

        Args:
            db: Database session
            hashed_key: Hashed API key

        Returns:
            APIKey instance or None if not found
        """
        result = await db.execute(select(APIKey).where(APIKey.key == hashed_key))
        return result.scalars().first()

    async def verify_and_get(
        self,
        db: AsyncSession,
        *,
        plain_key: str
    ) -> Optional[APIKey]:
        """
        Verify a plain text API key and return the APIKey object if valid.

        This method checks all active keys in the database to find a match.
        Updates last_used_at timestamp on successful verification.

        Args:
            db: Database session
            plain_key: Plain text API key to verify

        Returns:
            APIKey instance if valid, None otherwise
        """
        # Get all active API keys
        result = await db.execute(
            select(APIKey).where(APIKey.is_active == True)
        )
        api_keys = result.scalars().all()

        # Check each key
        for api_key in api_keys:
            if verify_api_key(plain_key, api_key.key):
                # Update last_used_at timestamp
                api_key.last_used_at = datetime.now(timezone.utc)
                await db.commit()
                await db.refresh(api_key)
                return api_key

        return None

    async def get_by_name(
        self,
        db: AsyncSession,
        *,
        name: str
    ) -> Optional[APIKey]:
        """
        Get API key by name.

        Args:
            db: Database session
            name: Key name

        Returns:
            APIKey instance or None if not found
        """
        result = await db.execute(select(APIKey).where(APIKey.name == name))
        return result.scalars().first()

    async def deactivate(self, db: AsyncSession, *, api_key: APIKey) -> APIKey:
        """
        Deactivate an API key.

        Args:
            db: Database session
            api_key: APIKey instance to deactivate

        Returns:
            Updated APIKey instance
        """
        api_key.is_active = False
        await db.commit()
        await db.refresh(api_key)
        return api_key

    async def activate(self, db: AsyncSession, *, api_key: APIKey) -> APIKey:
        """
        Activate an API key.

        Args:
            db: Database session
            api_key: APIKey instance to activate

        Returns:
            Updated APIKey instance
        """
        api_key.is_active = True
        await db.commit()
        await db.refresh(api_key)
        return api_key


# Create instance of CRUDAPIKey
api_key = CRUDAPIKey(APIKey)
