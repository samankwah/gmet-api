"""
Authentication dependencies.

This module contains dependency injection functions for authentication
and authorization.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.crud.user import user as user_crud

# Authentication now uses database-backed users with API keys
# No hardcoded keys - all authentication goes through the User model


def get_api_key_from_request(request: Request) -> str:
    """
    Extract API key from request headers.

    Supports both Authorization header (Bearer token) and X-API-Key header.

    Args:
        request: FastAPI request object

    Returns:
        API key string

    Raises:
        HTTPException: If API key is missing
    """
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    # Check X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key required. Provide it in Authorization header (Bearer token) or X-API-Key header",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def validate_api_key(
    api_key: str = Depends(get_api_key_from_request),
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Validate API key against the database.

    Args:
        api_key: API key to validate
        db: Database session

    Returns:
        Valid API key

    Raises:
        HTTPException: If API key is invalid
    """
    user_obj = await user_crud.get_by_api_key(db, api_key=api_key)

    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not await user_crud.is_active(user_obj):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return api_key

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from API key.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        User instance

    Raises:
        HTTPException: If API key is invalid or user not found
    """
    api_key = credentials.credentials

    # Get user by API key
    user_obj = await user_crud.get_by_api_key(db, api_key=api_key)

    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not await user_crud.is_active(user_obj):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )

    return user_obj


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current authenticated superuser.

    Args:
        current_user: Current authenticated user

    Returns:
        User instance (must be superuser)

    Raises:
        HTTPException: If user is not a superuser
    """
    if not await user_crud.is_superuser(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
