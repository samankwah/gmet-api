"""
Annual summary database model.

This module contains the AnnualSummary model for storing aggregated annual climate
statistics calculated from daily summaries.

Annual summaries are used in climate reports, WMO submissions, and long-term trend analysis.
"""

from sqlalchemy import Column, Float, Integer, Date, Index, UniqueConstraint, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AnnualSummary(BaseModel):
    """
    Annual climate summary data.

    Aggregates daily summaries into annual statistics for climate reports,
    WMO submissions, and long-term trend analysis.

    WMO-compliant aggregation rules:
    - Rainfall: SUM (never average)
    - Sunshine: SUM (never average)
    - Temperature: MEAN of daily Tmax/Tmin
    - Relative humidity: MEAN

    Requires at least 292 days of data (80% completeness) for valid aggregation.

    Includes tracking of:
    - Annual rainfall total and anomaly
    - Extreme temperature events with dates
    - Rainfall extremes with dates
    - Data completeness percentage

    Fields include:
    - Annual rainfall total, anomaly, and rainfall days
    - Maximum daily rainfall with date
    - Absolute temperature extremes with dates
    - Mean annual temperature and anomaly
    - Hot day counts (> 35°C and > 40°C)
    - Heavy rain day counts (> 50mm)
    - Mean annual relative humidity
    - Total annual sunshine hours
    - Data quality tracking
    """

    __tablename__ = "annual_summaries"

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
        comment="Calendar year"
    )

    # Rainfall statistics (WMO Rule: SUM, never average)
    rainfall_total = Column(
        Float,
        nullable=True,
        comment="Total annual rainfall in mm (SUM of 365 daily values)"
    )
    rainfall_anomaly = Column(
        Float,
        nullable=True,
        comment="Rainfall anomaly vs 30-year normal in mm (absolute difference)"
    )
    rainfall_anomaly_percent = Column(
        Float,
        nullable=True,
        comment="Rainfall anomaly as percentage of normal"
    )
    rainfall_days = Column(
        Integer,
        nullable=True,
        comment="Number of days with rainfall >= 1mm"
    )
    max_daily_rainfall = Column(
        Float,
        nullable=True,
        comment="Maximum daily rainfall in mm during the year"
    )
    max_daily_rainfall_date = Column(
        Date,
        nullable=True,
        comment="Date of maximum daily rainfall"
    )

    # Temperature statistics (WMO Rule: MEAN of daily Tmax/Tmin)
    temp_max_absolute = Column(
        Float,
        nullable=True,
        comment="Absolute maximum temperature in °C during the year"
    )
    temp_max_absolute_date = Column(
        Date,
        nullable=True,
        comment="Date of absolute maximum temperature"
    )
    temp_min_absolute = Column(
        Float,
        nullable=True,
        comment="Absolute minimum temperature in °C during the year"
    )
    temp_min_absolute_date = Column(
        Date,
        nullable=True,
        comment="Date of absolute minimum temperature"
    )
    temp_mean_annual = Column(
        Float,
        nullable=True,
        comment="Mean annual temperature in °C (average of all daily means)"
    )
    temp_anomaly = Column(
        Float,
        nullable=True,
        comment="Temperature anomaly vs 30-year normal in °C (absolute difference)"
    )

    # Extreme event counts
    hot_days_count = Column(
        Integer,
        nullable=True,
        comment="Number of days with Tmax > 35°C (heat stress)"
    )
    very_hot_days_count = Column(
        Integer,
        nullable=True,
        comment="Number of days with Tmax > 40°C (extreme heat)"
    )
    heavy_rain_days = Column(
        Integer,
        nullable=True,
        comment="Number of days with rainfall > 50mm (heavy rainfall events)"
    )

    # Other statistics
    mean_rh_annual = Column(
        Integer,
        nullable=True,
        comment="Mean annual relative humidity in %"
    )

    # Sunshine statistics (WMO Rule: SUM, never average)
    sunshine_total = Column(
        Float,
        nullable=True,
        comment="Total annual sunshine hours (SUM of 365 daily values, theoretical max ~4380h)"
    )

    # Data quality
    data_completeness_percent = Column(
        Float,
        nullable=True,
        comment="Percentage of days with valid observations (days_with_data / 365 * 100)"
    )

    # Relationship to station
    station = relationship("Station", back_populates="annual_summaries")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('station_id', 'year', name='uq_annual_station_year'),
        Index('idx_annual_station_year', 'station_id', 'year'),
        Index('idx_annual_year', 'year'),
        CheckConstraint('data_completeness_percent >= 0 AND data_completeness_percent <= 100', name='check_annual_completeness_valid'),
    )

    def __repr__(self):
        return f"<AnnualSummary(id={self.id}, station_id={self.station_id}, year={self.year})>"
