"""
Seasonal summary database model.

This module contains the SeasonalSummary model for storing aggregated seasonal climate
statistics calculated from daily summaries.

Seasonal summaries follow Ghana-specific climate seasons (MAM, JJA, SON, DJF).
Used for seasonal forecasts, agricultural planning, and climate monitoring.
"""

from sqlalchemy import Column, Float, Integer, Date, String, Index, UniqueConstraint, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class SeasonalSummary(BaseModel):
    """
    Seasonal climate summary data.

    Aggregates daily summaries into seasonal statistics for seasonal forecasts,
    agricultural planning, and climate monitoring.

    Ghana-specific seasons (following West African climate patterns):
    - MAM (March-April-May): Major rainy season - primary planting period
    - JJA (June-July-August): Minor rainy season - important for southern Ghana
    - SON (September-October-November): Post-rainy/transition - harvest period
    - DJF (December-January-February): Dry season/Harmattan - lowest rainfall

    WMO-compliant aggregation rules:
    - Rainfall: SUM (never average)
    - Sunshine: SUM (never average)
    - Temperature: MEAN of daily Tmax/Tmin
    - Relative humidity: MEAN
    - Wind speed: MEAN

    Requires at least 63 days of data (70% completeness) for valid aggregation.

    Critical for agriculture:
    - Onset date: When rainy season begins (for planting decisions)
    - Cessation date: When rainy season ends (for harvest planning)
    - Season length: Days between onset and cessation
    - Dry spells: Consecutive days without rain (crop stress indicator)

    Fields include:
    - Seasonal rainfall total, anomaly, and rainy days
    - Onset/cessation dates and season length
    - Dry spell analysis (count and maximum duration)
    - Mean and extreme temperatures
    - Hot days count (heat stress indicator)
    - Mean relative humidity and total sunshine
    """

    __tablename__ = "seasonal_summaries"

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
        comment="Calendar year (for DJF, year refers to December-January year)"
    )
    season = Column(
        String(3),
        nullable=False,
        comment="Season code: MAM, JJA, SON, or DJF"
    )
    start_date = Column(
        Date,
        nullable=False,
        comment="Start date of the season"
    )
    end_date = Column(
        Date,
        nullable=False,
        comment="End date of the season"
    )

    # Rainfall statistics (WMO Rule: SUM, never average)
    rainfall_total = Column(
        Float,
        nullable=True,
        comment="Total seasonal rainfall in mm (SUM of daily values)"
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

    # Agricultural timing indicators (CRITICAL for planting/harvest)
    onset_date = Column(
        Date,
        nullable=True,
        comment="Date when rainy season begins (WMO criteria: 20mm in 3 days, no 7-day dry spell in next 20 days)"
    )
    cessation_date = Column(
        Date,
        nullable=True,
        comment="Date when rainy season ends (last rainy day before < 10mm in 20 days)"
    )
    season_length_days = Column(
        Integer,
        nullable=True,
        comment="Number of days between onset and cessation (growing season length)"
    )

    # Dry spell analysis (crop stress indicator)
    max_dry_spell_days = Column(
        Integer,
        nullable=True,
        comment="Maximum consecutive days without rain (>= 1mm) during the season"
    )
    dry_spells_count = Column(
        Integer,
        nullable=True,
        comment="Number of dry spells >= 7 consecutive days (drought stress events)"
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
    temp_anomaly = Column(
        Float,
        nullable=True,
        comment="Temperature anomaly vs 30-year normal in °C (absolute difference)"
    )

    # Extreme temperature events
    hot_days_count = Column(
        Integer,
        nullable=True,
        comment="Number of days with Tmax > 35°C (heat stress threshold for crops)"
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
    station = relationship("Station", back_populates="seasonal_summaries")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('station_id', 'year', 'season', name='uq_seasonal_station_year_season'),
        Index('idx_seasonal_station_year', 'station_id', 'year'),
        CheckConstraint("season IN ('MAM', 'JJA', 'SON', 'DJF')", name='check_season_valid'),
    )

    def __repr__(self):
        return f"<SeasonalSummary(id={self.id}, station_id={self.station_id}, year={self.year}, season={self.season})>"
