"""
Authentication router.

This module contains authentication endpoints for API key management
and user authentication.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.auth import APIKeyResponse, TokenResponse, UserCreate, User as UserSchema
from app.models.user import User
from app.crud.user import user as crud_user
from app.utils.security import verify_password, create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={401: {"description": "Unauthorized"}},
)

security = HTTPBearer()
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # Strict limit to prevent brute force attacks
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access token.

    Authenticates a user using email (as username) and password,
    then returns a JWT access token and user information.

    Rate limit: 5 requests per minute (to prevent brute force attacks)

    Args:
        request: FastAPI request object
        form_data: OAuth2 form with username (email) and password
        db: Database session

    Returns:
        TokenResponse with access token, token type, user info, and expiration

    Raises:
        HTTPException: If credentials are invalid or user is inactive
    """
    # Get user by email (username field contains email)
    user_obj = await crud_user.get_by_email(db, email=form_data.username)

    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(form_data.password, user_obj.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_obj.email},
        expires_delta=access_token_expires
    )

    # Convert to Pydantic schema
    user_schema = UserSchema(
        id=user_obj.id,
        email=user_obj.email,
        is_active=user_obj.is_active,
        is_superuser=user_obj.is_superuser,
        api_key=user_obj.api_key,
        created_at=user_obj.created_at,
        updated_at=user_obj.updated_at
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_schema,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )


@router.post("/register", response_model=APIKeyResponse)
@limiter.limit("3/hour")  # Limit registration attempts
async def register_user(
    request: Request,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user and generate API key.

    Creates a new user account with email and password,
    automatically generates a secure API key.

    Rate limit: 3 requests per hour

    Args:
        request: FastAPI request object
        user_in: User registration data (email, password)
        db: Database session

    Returns:
        APIKeyResponse with user ID, email, API key, and creation timestamp

    Raises:
        HTTPException: If email is already registered
    """
    # Check if user already exists
    existing_user = await crud_user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user (password will be hashed and API key generated automatically)
    new_user = await crud_user.create(db, obj_in=user_in)

    return APIKeyResponse(
        user_id=new_user.id,
        email=new_user.email,
        api_key=new_user.api_key,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )


@router.get("/me", response_model=APIKeyResponse)
@limiter.limit("30/minute")
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information and API key details.

    Rate limit: 30 requests per minute
    """
    return APIKeyResponse(
        user_id=current_user.id,
        email=current_user.email,
        api_key=current_user.api_key,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@router.post("/apikey/regenerate", response_model=APIKeyResponse)
@limiter.limit("3/hour")  # Strict limit for security-sensitive operation
async def regenerate_api_key(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate API key for current user.

    Creates a new secure API key for the authenticated user,
    invalidating the previous key.

    Rate limit: 3 requests per hour (security-sensitive operation)

    Args:
        request: FastAPI request object
        current_user: Currently authenticated user
        db: Database session

    Returns:
        APIKeyResponse with new API key and user information

    Raises:
        HTTPException: If user is not active
    """
    from app.utils.security import generate_api_key

    # Check if user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Generate new API key
    new_api_key = generate_api_key()
    current_user.api_key = new_api_key

    # Save to database
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return APIKeyResponse(
        user_id=current_user.id,
        email=current_user.email,
        api_key=current_user.api_key,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
