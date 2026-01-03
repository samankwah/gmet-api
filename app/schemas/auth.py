"""
Authentication schemas.

This module contains Pydantic schemas for authentication requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.schemas.base import BaseSchema, TimestampSchema


class Token(BaseModel):
    """Token schema for authentication."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data payload."""
    email: Optional[str] = None


class UserBase(BaseSchema):
    """Base user schema."""
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str


class UserUpdate(UserBase):
    """Schema for updating user information."""
    password: Optional[str] = None


class User(UserBase, TimestampSchema):
    """Complete user schema with timestamps."""
    id: int
    api_key: str


class APIKeyResponse(BaseSchema):
    """Response schema for API key information."""
    user_id: int
    email: EmailStr
    api_key: str
    is_active: bool
    created_at: datetime


class TokenResponse(Token):
    """Response schema for token generation."""
    user: User
    expires_in: int  # seconds
