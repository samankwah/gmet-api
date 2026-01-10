"""
Weekly summary database model.

This module contains the WeeklySummary model for storing aggregated weekly weather
statistics calculated from daily summaries.

Weekly summaries follow ISO 8601 week numbering (Monday start, weeks 1-53).
Used for media briefings and agriculture monitoring.
"""

from sqlalchemy import Column, Float, Integer, Date, Index, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class WeeklySummary(BaseModel):
    """
    Weekly weather summary data.

    Aggregates daily summaries into weekly statistics for media briefings
    and agricultural monitoring.

    Follows ISO 8601 week numbering:
    - Week starts on Monday
    - Week 1 is the first week with at least 4 days in the new year
    - Week numbers range from 1-53

    WMO-compliant aggregation rules:
    - Rainfall: SUM (never average)
    - Sunshine: SUM (never average)
    - Temperature: MEAN of daily Tmax/Tmin
    - Relative humidity: MEAN
    - Wind speed: MEAN

    Requires at least 5 days of data (70% completeness) for valid aggregation.

    Fields include:
    - Total weekly rainfall and wet days count
    - Mean and absolute temperature extremes
    - Mean relative humidity
    - Mean wind speed
    - Total sunshine hours
    """

    __tablename__ = "weekly_summaries"

    station_id = Column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the weather station"
    )
    year = Column(
        Integer,
        nullable=False,
        index=True,
        comment="ISO 8601 year (may differ from calendar year for week 1)"
    )
    week_number = Column(
        Integer,
        nullable=False,
        comment="ISO 8601 week number (1-53)"
    )
    start_date = Column(
        Date,
        nullable=False,
        comment="Monday start date of the week"
    )
    end_date = Column(
        Date,
        nullable=False,
        comment="Sunday end date of the week"
    )

    # Rainfall statistics (WMO Rule: SUM, never average)
    rainfall_total = Column(
        Float,
        nullable=True,
        comment="Total weekly rainfall in mm (SUM of 7 daily values)"
    )
    wet_days_count = Column(
        Integer,
        nullable=True,
        comment="Number of days with rainfall >= 1mm"
    )
    max_daily_rainfall = Column(
        Float,
        nullable=True,
        comment="Maximum daily rainfall in mm during the week"
    )

    # Temperature statistics (WMO Rule: MEAN of daily Tmax/Tmin)
    temp_max_mean = Column(
        Float,
        nullable=True,
        comment="Mean of daily maximum temperatures in °C"
    )
    temp_min_mean = Column(
        Float,
        nullable=True,
        comment="Mean of daily minimum temperatures in °C"
    )
    temp_max_absolute = Column(
        Float,
        nullable=True,
        comment="Absolute maximum temperature in °C during the week"
    )
    temp_min_absolute = Column(
        Float,
        nullable=True,
        comment="Absolute minimum temperature in °C during the week"
    )

    # Other statistics
    mean_rh = Column(
        Integer,
        nullable=True,
        comment="Mean relative humidity in % (average of daily means)"
    )
    mean_wind_speed = Column(
        Float,
        nullable=True,
        comment="Mean wind speed in m/s (average of daily means)"
    )

    # Sunshine statistics (WMO Rule: SUM, never average)
    sunshine_total = Column(
        Float,
        nullable=True,
        comment="Total sunshine hours (SUM of 7 daily values, max ~84 hours)"
    )

    # Relationship to station
    station = relationship("Station", back_populates="weekly_summaries")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('station_id', 'year', 'week_number', name='uq_weekly_station_year_week'),
        Index('idx_weekly_station_year_week', 'station_id', 'year', 'week_number'),
        Index('idx_weekly_year', 'year'),
    )

    def __repr__(self):
        return f"<WeeklySummary(id={self.id}, station_id={self.station_id}, year={self.year}, week={self.week_number})>"
