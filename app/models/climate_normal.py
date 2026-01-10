"""
Climate normal database model.

This module contains the ClimateNormal model for storing 30-year climate averages
used for anomaly calculations.

Climate normals follow WMO standards (30-year reference periods).
Current standard period: 1991-2020
"""

from sqlalchemy import Column, Float, Integer, String, Index, UniqueConstraint, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ClimateNormal(BaseModel):
    """
    Climate normal data (30-year averages).

    Stores 30-year average values for different timescales, used to calculate
    anomalies in climate products.

    WMO Standard Reference Period: 1991-2020 (current)
    Previous periods (for historical context): 1961-1990, 1971-2000, 1981-2010

    Supports multiple timescales:
    - Monthly: 12 values per station (Jan-Dec averages)
    - Dekadal: 36 values per station (12 months × 3 dekads)
    - Seasonal: 4 values per station (MAM, JJA, SON, DJF)
    - Annual: 1 value per station (yearly average)

    Includes standard deviations for calculating standardized anomalies.

    Fields include:
    - Station and period identification
    - Timescale (monthly, dekadal, seasonal, annual)
    - Period specifiers (month, dekad, season as applicable)
    - Rainfall normal and standard deviation
    - Temperature normals (max, min, mean) and standard deviation
    - Sunshine normal
    - Metadata for tracking computation
    """

    __tablename__ = "climate_normals"

    station_id = Column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the weather station"
    )
    normal_period_start = Column(
        Integer,
        nullable=False,
        comment="Start year of the 30-year normal period (e.g., 1991)"
    )
    normal_period_end = Column(
        Integer,
        nullable=False,
        comment="End year of the 30-year normal period (e.g., 2020)"
    )
    timescale = Column(
        String(20),
        nullable=False,
        comment="Timescale: 'monthly', 'dekadal', 'seasonal', or 'annual'"
    )

    # Period specifiers (nullable, depends on timescale)
    month = Column(
        Integer,
        nullable=True,
        comment="Month number (1-12) for monthly and dekadal normals, NULL otherwise"
    )
    dekad = Column(
        Integer,
        nullable=True,
        comment="Dekad number (1-3) for dekadal normals only, NULL otherwise"
    )
    season = Column(
        String(3),
        nullable=True,
        comment="Season code (MAM, JJA, SON, DJF) for seasonal normals only, NULL otherwise"
    )

    # Rainfall normals (30-year averages)
    rainfall_normal = Column(
        Float,
        nullable=True,
        comment="30-year mean rainfall in mm for this period"
    )
    rainfall_std = Column(
        Float,
        nullable=True,
        comment="Standard deviation of rainfall across 30 years (for standardized anomalies)"
    )

    # Temperature normals (30-year averages)
    temp_max_normal = Column(
        Float,
        nullable=True,
        comment="30-year mean of maximum temperatures in °C"
    )
    temp_min_normal = Column(
        Float,
        nullable=True,
        comment="30-year mean of minimum temperatures in °C"
    )
    temp_mean_normal = Column(
        Float,
        nullable=True,
        comment="30-year mean temperature in °C"
    )
    temp_std = Column(
        Float,
        nullable=True,
        comment="Standard deviation of mean temperature across 30 years"
    )

    # Sunshine normal (30-year average)
    sunshine_normal = Column(
        Float,
        nullable=True,
        comment="30-year mean sunshine hours for this period"
    )

    # Data quality metadata
    years_with_data = Column(
        Integer,
        nullable=True,
        comment="Number of years (out of 30) with sufficient data for this calculation"
    )
    data_completeness_percent = Column(
        Float,
        nullable=True,
        comment="Percentage of expected data available across the 30-year period"
    )

    # Relationship to station
    station = relationship("Station", back_populates="climate_normals")

    # Constraints and indexes
    __table_args__ = (
        # Unique constraint covering all identifying fields
        UniqueConstraint(
            'station_id', 'normal_period_start', 'normal_period_end',
            'timescale', 'month', 'dekad', 'season',
            name='uq_climate_normal_unique'
        ),
        Index('idx_climate_normal_station_period', 'station_id', 'normal_period_start', 'normal_period_end'),
        Index('idx_climate_normal_timescale', 'timescale'),
        CheckConstraint("timescale IN ('monthly', 'dekadal', 'seasonal', 'annual')", name='check_timescale_valid'),
        CheckConstraint('month IS NULL OR (month >= 1 AND month <= 12)', name='check_climate_normal_month_valid'),
        CheckConstraint('dekad IS NULL OR (dekad >= 1 AND dekad <= 3)', name='check_climate_normal_dekad_valid'),
        CheckConstraint("season IS NULL OR season IN ('MAM', 'JJA', 'SON', 'DJF')", name='check_climate_normal_season_valid'),
        CheckConstraint('data_completeness_percent >= 0 AND data_completeness_percent <= 100', name='check_climate_normal_completeness_valid'),
        CheckConstraint('years_with_data >= 0 AND years_with_data <= 30', name='check_years_with_data_valid'),
    )

    def __repr__(self):
        period_info = ""
        if self.month:
            period_info = f", month={self.month}"
        if self.dekad:
            period_info += f", dekad={self.dekad}"
        if self.season:
            period_info = f", season={self.season}"
        return f"<ClimateNormal(id={self.id}, station_id={self.station_id}, {self.normal_period_start}-{self.normal_period_end}, {self.timescale}{period_info})>"
