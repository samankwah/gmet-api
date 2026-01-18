"""
Authentication dependencies.

This module contains dependency injection functions for authentication
and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.api_key import APIKey
from app.crud.user import user as user_crud
from app.crud.api_key import api_key as api_key_crud

# Authentication now uses database-backed users with API keys
# No hardcoded keys - all authentication goes through the User model
# New APIKey model provides separate API key authentication


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


# Define the API key header security scheme for Swagger UI
api_key_header_scheme = APIKeyHeader(
    name="X-API-Key",
    scheme_name="ApiKeyAuth",  # Must match the name in OpenAPI schema
    auto_error=False  # Don't auto-raise, we'll handle errors manually
)


async def get_api_key(
    api_key_value: str = Security(api_key_header_scheme),
    db: AsyncSession = Depends(get_db)
) -> APIKey:
    """
    Get and validate API key from X-API-Key header.

    Uses FastAPI's Security system to properly document the API key requirement
    in OpenAPI/Swagger UI, while maintaining backward compatibility with existing clients.

    Args:
        api_key_value: API key from X-API-Key header (extracted by FastAPI)
        db: Database session

    Returns:
        APIKey instance if valid

    Raises:
        HTTPException: 401 if API key is missing, invalid, or inactive
    """
    if not api_key_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide it in X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify the API key
    api_key_obj = await api_key_crud.verify_and_get(db, plain_key=api_key_value)

    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not api_key_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is inactive",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key_obj


async def get_api_key_optional(
    api_key_value: str = Security(api_key_header_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[APIKey]:
    """
    Optional API key validation - returns None instead of 401 if not provided.

    This allows endpoints to work without authentication while still supporting
    authenticated access for higher rate limits or additional features.

    Args:
        api_key_value: API key from X-API-Key header (extracted by FastAPI)
        db: Database session

    Returns:
        APIKey instance if valid, None if not provided or invalid
    """
    if not api_key_value:
        return None  # Allow unauthenticated access

    # Verify the API key if provided
    api_key_obj = await api_key_crud.verify_and_get(db, plain_key=api_key_value)

    if not api_key_obj:
        return None  # Invalid key, but still allow access (just not authenticated)

    if not api_key_obj.is_active:
        return None  # Inactive key, but still allow access

    return api_key_obj


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


async def get_current_admin_api_key(
    api_key: APIKey = Depends(get_api_key),
) -> APIKey:
    """
    Get current authenticated API key with admin role.

    Args:
        api_key: Current authenticated API key

    Returns:
        APIKey instance (must have admin role)

    Raises:
        HTTPException: If API key does not have admin role
    """
    if api_key.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return api_key


# """
# Authentication dependencies for FastAPI endpoints.
# """

# from typing import Optional
# from fastapi import Depends, HTTPException, Security, status
# from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# import bcrypt  # Use bcrypt directly
# from jose import JWTError, jwt
# from datetime import datetime, timezone

# from app.database import get_db
# from app.models.api_key import APIKey
# from app.models.user import User
# from app.config import settings

# # Define the API key header security scheme
# api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# # HTTP Bearer for JWT tokens
# security = HTTPBearer(auto_error=False)


# async def get_api_key(
#     api_key_header: str = Security(api_key_header),
#     db: AsyncSession = Depends(get_db)
# ) -> APIKey:
#     """
#     Validate API key from request header.
    
#     Args:
#         api_key_header: API key from X-API-Key header
#         db: Database session
        
#     Returns:
#         APIKey: Valid and active API key object
        
#     Raises:
#         HTTPException: If API key is missing, invalid, or inactive
#     """
#     if not api_key_header:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Missing API Key. Please provide X-API-Key header.",
#             headers={"WWW-Authenticate": "ApiKey"}
#         )
    
#     # Get all active API keys from database
#     result = await db.execute(
#         select(APIKey).where(APIKey.is_active == True)
#     )
#     api_keys = result.scalars().all()
    
#     # Check if provided key matches any hashed key using bcrypt
#     matched_key = None
#     for db_key in api_keys:
#         try:
#             if bcrypt.checkpw(api_key_header.encode('utf-8'), db_key.key.encode('utf-8')):
#                 matched_key = db_key
#                 break
#         except Exception:
#             continue
    
#     if not matched_key:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid API Key",
#             headers={"WWW-Authenticate": "ApiKey"}
#         )
    
#     # Update last_used_at timestamp
#     matched_key.last_used_at = datetime.now(timezone.utc)
#     await db.commit()
    
#     return matched_key


# async def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Security(security),
#     db: AsyncSession = Depends(get_db)
# ) -> User:
#     """
#     Validate JWT token and return current user.
    
#     Args:
#         credentials: JWT token from Authorization header
#         db: Database session
        
#     Returns:
#         User: Current authenticated user
        
#     Raises:
#         HTTPException: If token is missing, invalid, or user not found
#     """
#     if not credentials:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Missing authentication token",
#             headers={"WWW-Authenticate": "Bearer"}
#         )
    
#     try:
#         payload = jwt.decode(
#             credentials.credentials,
#             settings.SECRET_KEY,
#             algorithms=[settings.ALGORITHM]
#         )
#         user_id: str = payload.get("sub")
        
#         if user_id is None:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Invalid authentication token",
#                 headers={"WWW-Authenticate": "Bearer"}
#             )
            
#     except JWTError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid authentication token",
#             headers={"WWW-Authenticate": "Bearer"}
#         )
    
#     result = await db.execute(
#         select(User).where(User.id == int(user_id))
#     )
#     user = result.scalar_one_or_none()
    
#     if user is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User not found"
#         )
    
#     if not user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Inactive user"
#         )
    
#     return user


# async def get_current_active_user(
#     current_user: User = Depends(get_current_user)
# ) -> User:
#     """Get current active user (convenience function)."""
#     return current_user


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     """Verify a password against its hash."""
#     return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# def get_password_hash(password: str) -> str:
#     """Hash a password."""
#     return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')