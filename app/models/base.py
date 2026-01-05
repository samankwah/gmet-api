"""
Base database model with common fields and functionality.

This module contains the base SQLAlchemy model with common fields
like id, created_at, updated_at that other models can inherit from.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import func

from app.database import Base


class BaseModel(Base):
    """
    Base model with common database fields.

    All other models should inherit from this class to get
    automatic id, created_at, and updated_at fields.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    @declared_attr
    def created_at(cls):
        """Timestamp when record was created."""
        return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        """Timestamp when record was last updated."""
        return Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of the model instance."""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


