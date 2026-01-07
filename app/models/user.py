"""
User database model.

This module contains the User model for API key authentication.
"""

from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class User(BaseModel):
    """
    User model for API authentication.

    Represents API users who can access weather data endpoints.
    """

    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(String(50), default="user")  # user, admin, partner

    # Relationship to weather data (if user owns data)
    # weather_data = relationship("WeatherData", back_populates="owner")






