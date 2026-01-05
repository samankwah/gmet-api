"""
Synoptic observation database model.

This module contains the SynopticObservation model for storing weather observations
from GMet automatic weather stations at standard SYNOP reporting times.

Observations are captured at fixed times: 0600, 0900, 1200, and 1500 UTC (Ghana time).
These match the standard synoptic observation schedule used by meteorological agencies
worldwide for weather reporting and forecasting.
"""

from sqlalchemy import Column, Float, DateTime, ForeignKey, Integer, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class SynopticObservation(BaseModel):
    """
    Synoptic weather observation data.

    Stores instantaneous weather measurements from automatic weather stations
    at standard SYNOP reporting times: 0600, 0900, 1200, and 1500 UTC.

    Each observation contains:
    - Instantaneous temperature, relative humidity, wind speed/direction, pressure
    - Rainfall amount since the last observation (typically 3-hourly accumulation)

    Note: In future implementations, a validator can be added to ensure
    obs_datetime.hour is in [6, 9, 12, 15] to enforce the SYNOP schedule.
    """

    __tablename__ = "synoptic_observations"

    station_id = Column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the weather station"
    )
    obs_datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Exact observation time (e.g., 2026-01-04 06:00:00+00:00)"
    )

    # Weather measurements
    temperature = Column(
        Float,
        nullable=True,
        comment="Instantaneous air temperature in °C"
    )
    relative_humidity = Column(
        Integer,
        nullable=True,
        comment="Relative humidity in % (0-100)"
    )
    wind_speed = Column(
        Float,
        nullable=True,
        comment="Wind speed in m/s"
    )
    wind_direction = Column(
        Integer,
        nullable=True,
        comment="Wind direction in degrees (0-360, where 0=North)"
    )
    pressure = Column(
        Float,
        nullable=True,
        comment="Station pressure in hPa"
    )
    rainfall = Column(
        Float,
        nullable=True,
        comment="Rainfall since last observation in mm (typically 3-hourly accumulation)"
    )

    # Relationship to station
    station = relationship("Station", back_populates="synoptic_observations")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('station_id', 'obs_datetime', name='uq_synoptic_station_datetime'),
        Index('idx_synoptic_station_datetime', 'station_id', 'obs_datetime'),
        Index('idx_synoptic_datetime_station', 'obs_datetime', 'station_id'),
        Index('idx_synoptic_datetime', 'obs_datetime'),
    )

    def __repr__(self):
        return f"<SynopticObservation(id={self.id}, station_id={self.station_id}, obs_datetime={self.obs_datetime})>"

