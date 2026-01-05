"""
Status router.

This module contains endpoints for API status and health checks.
"""

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies.auth import get_api_key
from app.models.api_key import APIKey

router = APIRouter(
    prefix="/status",
    tags=["status"],
    responses={
        401: {"description": "Unauthorized"},
    },
)

limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=dict)
@limiter.limit("60/minute")
async def get_status(
    request: Request,
    api_key: APIKey = Depends(get_api_key)
):
    """
    Get API status.

    Requires valid API key authentication.

    Rate limit: 60 requests per minute

    Returns:
        dict: Status information
    """
    return {
        "status": "ok",
        "authenticated": True,
        "api_key_name": api_key.name,  # Show API key name
        "api_key_role": api_key.role
    }
