"""
API Key management endpoints.

This module contains endpoints for creating and managing API keys.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.api_key import APIKeyCreate, APIKeyCreateResponse, APIKeyResponse
from app.crud.api_key import api_key as api_key_crud
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api-keys",
    tags=["API Keys"],
    responses={
        401: {"description": "Unauthorized"},
        400: {"description": "Bad Request"},
    },
)


@router.post(
    "/",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="Create a new API key. The plain text key is returned only once - store it securely!",
)
async def create_api_key(
    api_key_data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key.

    **Note:** This endpoint is currently open (no authentication required).
    It will be secured with admin role checks in the next phase.

    The plain text API key is returned in the response and will never be shown again.
    Store it securely immediately!

    **Request Body:**
    ```json
    {
        "name": "Internal Dashboard",
        "role": "read_only"
    }
    ```

    **Response:**
    ```json
    {
        "id": 1,
        "name": "Internal Dashboard",
        "role": "read_only",
        "key": "abc123...",
        "message": "Store this key securely – it will not be shown again!"
    }
    ```

    Args:
        api_key_data: API key creation data (name and role)
        db: Database session

    Returns:
        APIKeyCreateResponse: Created API key with plain text key (shown only once)

    Raises:
        HTTPException: 400 if role is invalid
    """
    # Validate role
    valid_roles = ["admin", "read_only", "partner"]
    if api_key_data.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    logger.info(f"Creating API key: name={api_key_data.name}, role={api_key_data.role}")

    # Create the API key
    api_key_obj, plain_key = await api_key_crud.create(
        db,
        name=api_key_data.name,
        role=api_key_data.role,
        is_active=True
    )

    logger.info(f"API key created: id={api_key_obj.id}, name={api_key_obj.name}")

    return APIKeyCreateResponse(
        id=api_key_obj.id,
        name=api_key_obj.name,
        role=api_key_obj.role,
        key=plain_key,
        message="Store this key securely – it will not be shown again!"
    )


@router.get(
    "/",
    response_model=List[APIKeyResponse],
    summary="List all API keys",
    description="Get a list of all API keys (masked, no sensitive data). Admin only (to be secured in next phase).",
)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
):
    """
    List all API keys.

    **Note:** This endpoint is currently open (no authentication required).
    It will be secured with admin role checks in the next phase.

    Returns a list of API keys with their metadata, but no sensitive key data.

    **Response:**
    ```json
    [
        {
            "id": 1,
            "name": "Internal Dashboard",
            "role": "read_only",
            "is_active": true,
            "created_at": "2026-01-04T12:00:00Z",
            "last_used_at": null
        }
    ]
    ```

    Args:
        db: Database session

    Returns:
        List[APIKeyResponse]: List of API keys (without sensitive data)
    """
    logger.info("Listing all API keys")

    api_keys = await api_key_crud.get_multi(db, skip=0, limit=1000)

    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            role=key.role,
            is_active=key.is_active,
            created_at=key.created_at,
            last_used_at=key.last_used_at
        )
        for key in api_keys
    ]
