"""
User CRUD operations.

This module contains CRUD operations specific to user management.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.auth import UserCreate, UserUpdate
from app.utils.security import get_password_hash, generate_api_key


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    CRUD operations for User model.
    """

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """
        Create a new user with hashed password and generated API key.

        Args:
            db: Database session
            obj_in: User creation data

        Returns:
            Created user instance
        """
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser,
            api_key=generate_api_key()
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            db: Database session
            email: User email address

        Returns:
            User instance or None if not found
        """
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_by_api_key(self, db: AsyncSession, *, api_key: str) -> Optional[User]:
        """
        Get user by API key.

        Args:
            db: Database session
            api_key: User's API key

        Returns:
            User instance or None if not found
        """
        result = await db.execute(select(User).where(User.api_key == api_key))
        return result.scalars().first()

    async def is_active(self, user: User) -> bool:
        """
        Check if user is active.

        Args:
            user: User instance

        Returns:
            True if user is active, False otherwise
        """
        return user.is_active

    async def is_superuser(self, user: User) -> bool:
        """
        Check if user is a superuser.

        Args:
            user: User instance

        Returns:
            True if user is superuser, False otherwise
        """
        return user.is_superuser


# Create instance of CRUDUser
user = CRUDUser(User)
