"""
Status router.

This module contains endpoints for API status and health checks.
"""

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies.auth import validate_api_key

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
    api_key: str = Depends(validate_api_key)
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
        "api_key": api_key[:8] + "..."  # Show first 8 chars for security
    }
