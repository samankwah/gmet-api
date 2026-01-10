"""
Dekadal summary database model.

This module contains the DekadalSummary model for storing aggregated 10-day climate
statistics calculated from daily summaries.

Dekadal summaries are widely used in agrometeorological monitoring and forecasting.
"""

from sqlalchemy import Column, Float, Integer, Date, Index, UniqueConstraint, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class DekadalSummary(BaseModel):
    """
    Dekadal climate summary data (10-day periods).

    Aggregates daily summaries into dekadal statistics for agrometeorological
    monitoring and climate bulletins.

    CRITICAL - Dekad definitions (NOT arbitrary 10-day windows):
    - Dekad 1: Days 1-10 of the month
    - Dekad 2: Days 11-20 of the month
    - Dekad 3: Days 21 to end of month (28/29/30/31 depending on month)

    WMO-compliant aggregation rules:
    - Rainfall: SUM (never average)
    - Sunshine: SUM (never average)
    - Temperature: MEAN of daily Tmax/Tmin
    - Relative humidity: MEAN
    - Wind speed: MEAN

    Requires at least 7 days of data (70% completeness) for valid aggregation.

    Fields include:
    - Dekadal rainfall total and rainy days
    - Mean and extreme temperatures
    - Mean relative humidity
    - Total sunshine hours
    """

    __tablename__ = "dekadal_summaries"

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
    dekad = Column(
        Integer,
        nullable=False,
        comment="Dekad number: 1 (days 1-10), 2 (days 11-20), 3 (days 21-EOM)"
    )
    start_date = Column(
        Date,
        nullable=False,
        comment="Start date of the dekad"
    )
    end_date = Column(
        Date,
        nullable=False,
        comment="End date of the dekad"
    )

    # Rainfall statistics (WMO Rule: SUM, never average)
    rainfall_total = Column(
        Float,
        nullable=True,
        comment="Total dekadal rainfall in mm (SUM of daily values)"
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
    rainy_days = Column(
        Integer,
        nullable=True,
        comment="Number of days with rainfall >= 1mm"
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
        comment="Absolute maximum temperature in °C during the dekad"
    )
    temp_min_absolute = Column(
        Float,
        nullable=True,
        comment="Absolute minimum temperature in °C during the dekad"
    )

    # Other statistics
    mean_rh = Column(
        Integer,
        nullable=True,
        comment="Mean relative humidity in % (average of daily means)"
    )

    # Sunshine statistics (WMO Rule: SUM, never average)
    sunshine_total = Column(
        Float,
        nullable=True,
        comment="Total sunshine hours (SUM of daily values)"
    )

    # Relationship to station
    station = relationship("Station", back_populates="dekadal_summaries")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('station_id', 'year', 'month', 'dekad', name='uq_dekadal_station_year_month_dekad'),
        Index('idx_dekadal_station_year_month', 'station_id', 'year', 'month'),
        CheckConstraint('dekad >= 1 AND dekad <= 3', name='check_dekad_valid'),
        CheckConstraint('month >= 1 AND month <= 12', name='check_dekadal_month_valid'),
    )

    def __repr__(self):
        return f"<DekadalSummary(id={self.id}, station_id={self.station_id}, year={self.year}, month={self.month}, dekad={self.dekad})>"
