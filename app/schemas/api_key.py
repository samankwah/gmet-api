"""
API Key schemas.

This module contains Pydantic schemas for API key requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema, TimestampSchema


class APIKeyCreate(BaseSchema):
    """Schema for creating a new API key."""
    name: str = Field(..., description="Descriptive name for the key (e.g., 'Internal Dashboard', 'Mobile App')")
    role: str = Field(
        default="read_only",
        description="Key role: 'admin', 'read_only', or 'partner'",
        pattern="^(admin|read_only|partner)$"
    )


class APIKeyResponse(BaseSchema):
    """Schema for API key response (without sensitive data)."""
    id: int
    name: str
    role: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None


class APIKeyCreateResponse(BaseSchema):
    """Schema for API key creation response (includes plain text key shown only once)."""
    id: int
    name: str
    role: str
    key: str = Field(..., description="Plain text API key - store this securely, shown only once!")
    message: str = Field(
        default="Store this key securely – it will not be shown again!",
        description="Warning message"
    )
