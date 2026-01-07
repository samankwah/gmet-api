"""
Weather station database model.

This module contains the Station model representing physical weather monitoring
stations operated by the Ghana Meteorological Agency (GMet).
"""

from sqlalchemy import Column, String, Float, Integer, Index
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Station(BaseModel):
    """
    Weather station information.

    Represents physical weather monitoring stations across Ghana.
    Each station has a unique code (e.g., DGAA for Kotoka International Airport)
    and is located at specific coordinates.
    """

    __tablename__ = "stations"

    name = Column(String(200), nullable=False, index=True, comment="Station name")
    code = Column(String(50), unique=True, index=True, nullable=False, comment="Unique station code (e.g., DGAA)")
    latitude = Column(Float, nullable=False, comment="Latitude in degrees")
    longitude = Column(Float, nullable=False, comment="Longitude in degrees")
    region = Column(String(100), nullable=False, index=True, comment="Region or administrative area")

    # Relationships
    synoptic_observations = relationship(
        "SynopticObservation",
        back_populates="station",
        cascade="all, delete-orphan"
    )
    daily_summaries = relationship(
        "DailySummary",
        back_populates="station",
        cascade="all, delete-orphan"
    )

    # Create composite index for region and code queries
    __table_args__ = (
        Index('idx_station_region_code', 'region', 'code'),
    )

    def __repr__(self):
        return f"<Station(id={self.id}, code='{self.code}', name='{self.name}')>"

