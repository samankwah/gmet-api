"""
Daily summary database model.

This module contains the DailySummary model for storing aggregated daily weather
statistics calculated from synoptic observations.

Daily summaries are used in public bulletins and climatological reports.
They aggregate data over a 24-hour period (typically from 0600 UTC to 0600 UTC next day).
"""

from sqlalchemy import Column, Float, DateTime, ForeignKey, Integer, Date, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class DailySummary(BaseModel):
    """
    Daily weather summary data.

    Aggregates synoptic observations into daily statistics for public bulletins
    and climatological analysis.

    The daily period typically runs from 0600 UTC to 0600 UTC the next day,
    following GMet operational practice.

    Fields include:
    - Maximum and minimum temperatures with timestamps
    - Total 24-hour rainfall
    - Mean relative humidity (average of 0600, 0900, 1200, 1500 observations)
    - Maximum wind gust
    """

    __tablename__ = "daily_summaries"

    station_id = Column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the weather station"
    )
    date = Column(
        Date,
        nullable=False,
        index=True,
        comment="Observation date (e.g., 2026-01-04)"
    )

    # Temperature statistics
    temp_max = Column(
        Float,
        nullable=True,
        comment="Maximum temperature in °C over 24-hour period"
    )
    temp_max_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Time when maximum temperature was recorded"
    )
    temp_min = Column(
        Float,
        nullable=True,
        comment="Minimum temperature in °C over 24-hour period"
    )
    temp_min_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Time when minimum temperature was recorded"
    )

    # Precipitation
    rainfall_total = Column(
        Float,
        nullable=True,
        comment="Total 24-hour rainfall in mm (0600 to 0600 next day)"
    )

    # Other statistics
    mean_rh = Column(
        Integer,
        nullable=True,
        comment="Mean relative humidity in % (average of 0600, 0900, 1200, 1500 observations)"
    )
    wind_speed = Column(
        Float,
        nullable=True,
        comment="Mean wind speed in m/s over 24-hour period (average of available readings)"
    )
    sunshine_hours = Column(
        Float,
        nullable=True,
        comment="Total sunshine duration in hours during the 24-hour period"
    )

    # Relationship to station
    station = relationship("Station", back_populates="daily_summaries")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('station_id', 'date', name='uq_daily_station_date'),
        Index('idx_daily_station_date', 'station_id', 'date'),
        Index('idx_daily_date', 'date'),
    )

    def __repr__(self):
        return f"<DailySummary(id={self.id}, station_id={self.station_id}, date={self.date})>"

