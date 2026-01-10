"""
Monthly summary database model.

This module contains the MonthlySummary model for storing aggregated monthly climate
statistics calculated from daily summaries.

Monthly summaries are used in climate bulletins, research, and WMO reporting.
Includes anomaly calculations compared to 30-year climate normals (1991-2020).
"""

from sqlalchemy import Column, Float, Integer, Date, Index, UniqueConstraint, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class MonthlySummary(BaseModel):
    """
    Monthly climate summary data.

    Aggregates daily summaries into monthly statistics for climate bulletins,
    research, and policy decisions.

    WMO-compliant aggregation rules:
    - Rainfall: SUM (never average)
    - Sunshine: SUM (never average)
    - Temperature: MEAN of daily Tmax/Tmin
    - Relative humidity: MEAN
    - Wind speed: MEAN

    Requires at least 21 days of data (70% completeness) for valid aggregation.

    Anomaly calculations (if 1991-2020 climate normal exists):
    - Absolute anomaly = current_value - normal_value
    - Percent anomaly = ((current_value - normal_value) / normal_value) * 100

    Fields include:
    - Monthly rainfall total, anomaly, and rainfall days
    - Mean and extreme temperatures with anomalies
    - Mean relative humidity and wind speed
    - Total sunshine hours
    - Data completeness percentage
    """

    __tablename__ = "monthly_summaries"

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
    month = Column(
        Integer,
        nullable=False,
        index=True,
        comment="Month number (1-12)"
    )

    # Rainfall statistics (WMO Rule: SUM, never average)
    rainfall_total = Column(
        Float,
        nullable=True,
        comment="Total monthly rainfall in mm (SUM of daily values)"
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
        comment="Maximum daily rainfall in mm during the month"
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
    temp_mean = Column(
        Float,
        nullable=True,
        comment="Mean temperature in °C (average of temp_max_mean and temp_min_mean)"
    )
    temp_max_absolute = Column(
        Float,
        nullable=True,
        comment="Absolute maximum temperature in °C during the month"
    )
    temp_min_absolute = Column(
        Float,
        nullable=True,
        comment="Absolute minimum temperature in °C during the month"
    )
    temp_anomaly = Column(
        Float,
        nullable=True,
        comment="Temperature anomaly vs 30-year normal in °C (absolute difference)"
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
        comment="Total sunshine hours (SUM of daily values)"
    )

    # Data quality
    days_with_data = Column(
        Integer,
        nullable=True,
        comment="Number of days with valid observations in the month"
    )
    data_completeness_percent = Column(
        Float,
        nullable=True,
        comment="Percentage of days with valid observations (days_with_data / days_in_month * 100)"
    )

    # Relationship to station
    station = relationship("Station", back_populates="monthly_summaries")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('station_id', 'year', 'month', name='uq_monthly_station_year_month'),
        Index('idx_monthly_station_year_month', 'station_id', 'year', 'month'),
        Index('idx_monthly_year_month', 'year', 'month'),
        CheckConstraint('month >= 1 AND month <= 12', name='check_month_valid'),
        CheckConstraint('data_completeness_percent >= 0 AND data_completeness_percent <= 100', name='check_completeness_valid'),
    )

    def __repr__(self):
        return f"<MonthlySummary(id={self.id}, station_id={self.station_id}, year={self.year}, month={self.month})>"
