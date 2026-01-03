"""
Weather data database models.

This module contains models for storing weather station and observation data.
"""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, Index
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Station(BaseModel):
    """
    Weather station information.

    Represents physical weather monitoring stations.
    """

    __tablename__ = "stations"

    name = Column(String, nullable=False, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    region = Column(String, nullable=False, index=True)

    # Relationship to observations
    observations = relationship("Observation", back_populates="station", cascade="all, delete-orphan")

    # Create composite index for region and code queries
    __table_args__ = (
        Index('idx_station_region_code', 'region', 'code'),
    )

    def __repr__(self):
        return f"<Station(id={self.id}, code='{self.code}', name='{self.name}')>"


class Observation(BaseModel):
    """
    Weather observation data.

    Stores weather measurements from stations.
    """

    __tablename__ = "observations"

    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Weather measurements
    temperature = Column(Float)  # Celsius
    humidity = Column(Float)  # Percentage (0-100)
    wind_speed = Column(Float)  # m/s
    wind_direction = Column(Float)  # degrees (0-360)
    rainfall = Column(Float)  # mm
    pressure = Column(Float)  # hPa

    # Relationship to station
    station = relationship("Station", back_populates="observations")

    # Create composite indexes for common queries
    __table_args__ = (
        Index('idx_observation_station_timestamp', 'station_id', 'timestamp'),
        Index('idx_observation_timestamp_station', 'timestamp', 'station_id'),
    )

    def __repr__(self):
        return f"<Observation(id={self.id}, station_id={self.station_id}, timestamp={self.timestamp})>"
