"""
Base Pydantic schemas.

This module contains base schemas with common fields and configurations
that other schemas can inherit from.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Base schema with common configuration.

    All other schemas should inherit from this class.
    """

    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """
    Schema with timestamp fields.
    """

    created_at: datetime
    updated_at: datetime


class IDSchema(BaseSchema):
    """
    Schema with ID field.
    """

    id: int


