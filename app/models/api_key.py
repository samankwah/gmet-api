"""
API Key database model.

This module contains the APIKey model for API key authentication.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.sql import func

from app.models.base import BaseModel


class APIKey(BaseModel):
    """
    API Key model for authentication.

    Represents API keys used to authenticate requests to the API.
    Keys are hashed using bcrypt before storing in the database.
    """

    __tablename__ = "api_keys"

    key = Column(String(64), unique=True, index=True, nullable=False, comment="Hashed API key (bcrypt hash)")
    name = Column(String(200), nullable=False, comment="Descriptive name for the key (e.g., 'Internal Dashboard')")
    role = Column(String(50), nullable=False, default="read_only", comment="Role: 'admin', 'read_only', or 'partner'")
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether the key is active")
    last_used_at = Column(DateTime(timezone=True), nullable=True, comment="Timestamp of last use")

    # Create index for active keys lookup
    __table_args__ = (
        Index('idx_api_key_active', 'is_active'),
    )

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', role='{self.role}', is_active={self.is_active})>"


