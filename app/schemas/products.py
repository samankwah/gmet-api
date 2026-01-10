"""
Pydantic schemas for climate product responses.

This module defines response models for all climate product endpoints,
providing validation, documentation, and serialization for the API.
"""

from datetime import date as date_type, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# BASE SCHEMAS (for inheritance)
# ============================================================================

class ClimateProductBase(BaseModel):
    """Base schema for all climate products with common configuration."""

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# DAILY WEATHER PRODUCTS (Phase 1)
# ============================================================================

class DailyWeatherProductResponse(ClimateProductBase):
    """
    Daily weather product response.

    Maps directly to existing daily_summaries table - no new computation needed.
    Returns operational daily weather summaries for public bulletins.
    """
    id: int
    station_id: int
    date: date_type = Field(..., description="Observation date (YYYY-MM-DD)")

    # Temperature statistics
    temp_max: Optional[float] = Field(None, description="Maximum temperature °C")
    temp_min: Optional[float] = Field(None, description="Minimum temperature °C")
    temp_mean: Optional[float] = Field(None, description="Mean temperature °C [(Tmax + Tmin) / 2]")

    # Precipitation
    rainfall_total: Optional[float] = Field(None, description="Total 24-hour rainfall mm")

    # Humidity
    mean_rh: Optional[int] = Field(None, description="Mean relative humidity %")
    rh_0600: Optional[int] = Field(None, description="RH at 0600 UTC %")
    rh_0900: Optional[int] = Field(None, description="RH at 0900 UTC %")
    rh_1200: Optional[int] = Field(None, description="RH at 1200 UTC %")
    rh_1500: Optional[int] = Field(None, description="RH at 1500 UTC %")

    # Wind and sunshine
    wind_speed: Optional[float] = Field(None, description="Mean wind speed m/s")
    sunshine_hours: Optional[float] = Field(None, description="Total sunshine hours")

    # Metadata
    created_at: datetime
    updated_at: datetime


# ============================================================================
# WEEKLY SUMMARY (Phase 1)
# ============================================================================

class WeeklySummaryResponse(ClimateProductBase):
    """
    Weekly summary response for media briefings and agriculture monitoring.

    Follows ISO 8601 week numbering (Monday start, weeks 1-53).
    WMO-compliant aggregation: rainfall/sunshine summed, temperatures averaged.
    """
    id: int
    station_id: int
    year: int = Field(..., description="ISO 8601 year")
    week_number: int = Field(..., ge=1, le=53, description="ISO week number (1-53)")
    start_date: date_type = Field(..., description="Monday start date")
    end_date: date_type = Field(..., description="Sunday end date")

    # Rainfall statistics (WMO: SUM)
    rainfall_total: Optional[float] = Field(
        None,
        description="Total weekly rainfall mm (SUM of 7 daily values, WMO-compliant)"
    )
    wet_days_count: Optional[int] = Field(
        None,
        description="Number of days with rainfall >= 1mm"
    )
    max_daily_rainfall: Optional[float] = Field(
        None,
        description="Maximum daily rainfall mm during the week"
    )

    # Temperature statistics (WMO: MEAN)
    temp_max_mean: Optional[float] = Field(
        None,
        description="Mean of daily maximum temperatures °C (WMO-compliant)"
    )
    temp_min_mean: Optional[float] = Field(
        None,
        description="Mean of daily minimum temperatures °C (WMO-compliant)"
    )
    temp_max_absolute: Optional[float] = Field(
        None,
        description="Absolute maximum temperature °C during the week"
    )
    temp_min_absolute: Optional[float] = Field(
        None,
        description="Absolute minimum temperature °C during the week"
    )

    # Other statistics
    mean_rh: Optional[int] = Field(None, description="Mean relative humidity %")
    mean_wind_speed: Optional[float] = Field(None, description="Mean wind speed m/s")

    # Sunshine statistics (WMO: SUM)
    sunshine_total: Optional[float] = Field(
        None,
        description="Total sunshine hours (SUM of 7 daily values, max ~84h, WMO-compliant)"
    )

    # Metadata
    created_at: datetime
    updated_at: datetime


# ============================================================================
# MONTHLY CLIMATE SUMMARY (Phase 1)
# ============================================================================

class MonthlySummaryResponse(ClimateProductBase):
    """
    Monthly climate summary response for bulletins, research, and policy.

    WMO-compliant aggregation with anomaly calculations (vs 1991-2020 normals).
    Requires >= 70% data completeness (21+ days).
    """
    id: int
    station_id: int
    year: int = Field(..., description="Calendar year")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")

    # Rainfall statistics (WMO: SUM)
    rainfall_total: Optional[float] = Field(
        None,
        description="Total monthly rainfall mm (SUM of daily values, WMO-compliant)"
    )
    rainfall_anomaly: Optional[float] = Field(
        None,
        description="Rainfall anomaly vs 30-year normal mm (absolute difference). Null if normal unavailable."
    )
    rainfall_anomaly_percent: Optional[float] = Field(
        None,
        description="Rainfall anomaly as percentage of normal. Null if normal unavailable."
    )
    rainfall_days: Optional[int] = Field(
        None,
        description="Number of days with rainfall >= 1mm"
    )
    max_daily_rainfall: Optional[float] = Field(
        None,
        description="Maximum daily rainfall mm during the month"
    )

    # Temperature statistics (WMO: MEAN)
    temp_max_mean: Optional[float] = Field(
        None,
        description="Mean of daily maximum temperatures °C (WMO-compliant)"
    )
    temp_min_mean: Optional[float] = Field(
        None,
        description="Mean of daily minimum temperatures °C (WMO-compliant)"
    )
    temp_mean: Optional[float] = Field(
        None,
        description="Mean temperature °C [(Tmax_mean + Tmin_mean) / 2]"
    )
    temp_max_absolute: Optional[float] = Field(
        None,
        description="Absolute maximum temperature °C during the month"
    )
    temp_min_absolute: Optional[float] = Field(
        None,
        description="Absolute minimum temperature °C during the month"
    )
    temp_anomaly: Optional[float] = Field(
        None,
        description="Temperature anomaly vs 30-year normal °C (absolute difference). Null if normal unavailable."
    )

    # Other statistics
    mean_rh: Optional[int] = Field(None, description="Mean relative humidity %")
    mean_wind_speed: Optional[float] = Field(None, description="Mean wind speed m/s")

    # Sunshine statistics (WMO: SUM)
    sunshine_total: Optional[float] = Field(
        None,
        description="Total sunshine hours (SUM of daily values, WMO-compliant)"
    )

    # Data quality
    days_with_data: Optional[int] = Field(
        None,
        description="Number of days with valid observations"
    )
    data_completeness_percent: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Data completeness percentage (days_with_data / days_in_month * 100)"
    )

    # Metadata
    created_at: datetime
    updated_at: datetime


# ============================================================================
# STATION INFORMATION (for enriched responses)
# ============================================================================

class StationInfo(BaseModel):
    """Station information for enriched product responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str = Field(..., description="Station code (e.g., 23024TEM)")
    name: str = Field(..., description="Station name")
    latitude: float = Field(..., description="Latitude in degrees")
    longitude: float = Field(..., description="Longitude in degrees")
    region: str = Field(..., description="Administrative region")


# ============================================================================
# ENRICHED RESPONSES (with station info)
# ============================================================================

class WeeklySummaryWithStation(WeeklySummaryResponse):
    """Weekly summary enriched with station information."""
    station: StationInfo = Field(..., description="Station details")


class MonthlySummaryWithStation(MonthlySummaryResponse):
    """Monthly summary enriched with station information."""
    station: StationInfo = Field(..., description="Station details")


# ============================================================================
# DEKADAL SUMMARY (Phase 2)
# ============================================================================

class DekadalSummaryResponse(ClimateProductBase):
    """
    Dekadal summary response for agrometeorological monitoring.

    10-day climate products following WMO dekad definitions:
    - Dekad 1: Days 1-10
    - Dekad 2: Days 11-20
    - Dekad 3: Days 21-EOM (28/29/30/31)
    """
    id: int
    station_id: int
    year: int = Field(..., description="Calendar year")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    dekad: int = Field(..., ge=1, le=3, description="Dekad number (1, 2, or 3)")
    start_date: date_type = Field(..., description="Start date of dekad")
    end_date: date_type = Field(..., description="End date of dekad")

    # Rainfall statistics (WMO: SUM)
    rainfall_total: Optional[float] = Field(
        None,
        description="Total dekadal rainfall mm (SUM, WMO-compliant)"
    )
    rainfall_anomaly: Optional[float] = Field(
        None,
        description="Rainfall anomaly vs 30-year normal mm. Null if normal unavailable."
    )
    rainfall_anomaly_percent: Optional[float] = Field(
        None,
        description="Rainfall anomaly as percentage of normal. Null if normal unavailable."
    )
    rainy_days: Optional[int] = Field(
        None,
        description="Number of days with rainfall >= 1mm"
    )

    # Temperature statistics (WMO: MEAN)
    temp_max_mean: Optional[float] = Field(
        None,
        description="Mean of daily maximum temperatures °C (WMO-compliant)"
    )
    temp_min_mean: Optional[float] = Field(
        None,
        description="Mean of daily minimum temperatures °C (WMO-compliant)"
    )
    temp_max_absolute: Optional[float] = Field(
        None,
        description="Absolute maximum temperature °C during dekad"
    )
    temp_min_absolute: Optional[float] = Field(
        None,
        description="Absolute minimum temperature °C during dekad"
    )

    # Other statistics
    mean_rh: Optional[int] = Field(None, description="Mean relative humidity %")

    # Sunshine statistics (WMO: SUM)
    sunshine_total: Optional[float] = Field(
        None,
        description="Total sunshine hours (SUM, WMO-compliant)"
    )

    # Metadata
    created_at: datetime
    updated_at: datetime


# ============================================================================
# SEASONAL SUMMARY (Phase 2)
# ============================================================================

class SeasonalSummaryResponse(ClimateProductBase):
    """
    Seasonal summary response for agricultural planning and climate monitoring.

    Ghana-specific seasons:
    - MAM (March-May): Major rainy season - primary planting
    - JJA (June-August): Minor rainy season
    - SON (September-November): Post-rainy/transition - harvest
    - DJF (December-February): Dry season/Harmattan
    """
    id: int
    station_id: int
    year: int = Field(..., description="Calendar year (for DJF, December year)")
    season: str = Field(..., description="Season code: MAM, JJA, SON, or DJF")
    start_date: date_type = Field(..., description="Start date of season")
    end_date: date_type = Field(..., description="End date of season")

    # Rainfall statistics (WMO: SUM)
    rainfall_total: Optional[float] = Field(
        None,
        description="Total seasonal rainfall mm (SUM, WMO-compliant)"
    )
    rainfall_anomaly: Optional[float] = Field(
        None,
        description="Rainfall anomaly vs 30-year normal mm. Null if normal unavailable."
    )
    rainfall_anomaly_percent: Optional[float] = Field(
        None,
        description="Rainfall anomaly as percentage of normal. Null if normal unavailable."
    )
    rainy_days: Optional[int] = Field(
        None,
        description="Number of days with rainfall >= 1mm"
    )

    # Agricultural timing indicators (CRITICAL for planting/harvest decisions)
    onset_date: Optional[date_type] = Field(
        None,
        description="Rainy season onset date (WMO criteria: 20mm in 3 days). CRITICAL for planting."
    )
    cessation_date: Optional[date_type] = Field(
        None,
        description="Rainy season cessation date (< 10mm in 20 days). CRITICAL for harvest."
    )
    season_length_days: Optional[int] = Field(
        None,
        description="Growing season length (days between onset and cessation)"
    )

    # Dry spell analysis (crop stress indicators)
    max_dry_spell_days: Optional[int] = Field(
        None,
        description="Maximum consecutive days without rain during season"
    )
    dry_spells_count: Optional[int] = Field(
        None,
        description="Number of dry spells >= 7 consecutive days (drought stress events)"
    )

    # Temperature statistics (WMO: MEAN)
    temp_max_mean: Optional[float] = Field(
        None,
        description="Mean of daily maximum temperatures °C (WMO-compliant)"
    )
    temp_min_mean: Optional[float] = Field(
        None,
        description="Mean of daily minimum temperatures °C (WMO-compliant)"
    )
    temp_anomaly: Optional[float] = Field(
        None,
        description="Temperature anomaly vs 30-year normal °C. Null if normal unavailable."
    )

    # Extreme events
    hot_days_count: Optional[int] = Field(
        None,
        description="Number of days with Tmax > 35°C (heat stress threshold)"
    )

    # Other statistics
    mean_rh: Optional[int] = Field(None, description="Mean relative humidity %")

    # Sunshine statistics (WMO: SUM)
    sunshine_total: Optional[float] = Field(
        None,
        description="Total sunshine hours (SUM, WMO-compliant)"
    )

    # Metadata
    created_at: datetime
    updated_at: datetime


# ============================================================================
# ANNUAL SUMMARY (Phase 2)
# ============================================================================

class AnnualSummaryResponse(ClimateProductBase):
    """
    Annual summary response for climate reports and WMO submissions.

    Comprehensive annual statistics with extreme events tracking.
    Requires >= 80% data completeness (292+ days).
    """
    id: int
    station_id: int
    year: int = Field(..., description="Calendar year")

    # Rainfall statistics (WMO: SUM)
    rainfall_total: Optional[float] = Field(
        None,
        description="Total annual rainfall mm (SUM of 365 daily values, WMO-compliant)"
    )
    rainfall_anomaly: Optional[float] = Field(
        None,
        description="Rainfall anomaly vs 30-year normal mm. Null if normal unavailable."
    )
    rainfall_anomaly_percent: Optional[float] = Field(
        None,
        description="Rainfall anomaly as percentage of normal. Null if normal unavailable."
    )
    rainfall_days: Optional[int] = Field(
        None,
        description="Number of days with rainfall >= 1mm"
    )
    max_daily_rainfall: Optional[float] = Field(
        None,
        description="Maximum daily rainfall mm during the year"
    )
    max_daily_rainfall_date: Optional[date_type] = Field(
        None,
        description="Date of maximum daily rainfall"
    )

    # Temperature extremes with dates
    temp_max_absolute: Optional[float] = Field(
        None,
        description="Absolute maximum temperature °C during the year"
    )
    temp_max_absolute_date: Optional[date_type] = Field(
        None,
        description="Date of absolute maximum temperature"
    )
    temp_min_absolute: Optional[float] = Field(
        None,
        description="Absolute minimum temperature °C during the year"
    )
    temp_min_absolute_date: Optional[date_type] = Field(
        None,
        description="Date of absolute minimum temperature"
    )
    temp_mean_annual: Optional[float] = Field(
        None,
        description="Mean annual temperature °C"
    )
    temp_anomaly: Optional[float] = Field(
        None,
        description="Temperature anomaly vs 30-year normal °C. Null if normal unavailable."
    )

    # Extreme event counts
    hot_days_count: Optional[int] = Field(
        None,
        description="Number of days with Tmax > 35°C (heat stress)"
    )
    very_hot_days_count: Optional[int] = Field(
        None,
        description="Number of days with Tmax > 40°C (extreme heat)"
    )
    heavy_rain_days: Optional[int] = Field(
        None,
        description="Number of days with rainfall > 50mm (heavy rainfall events)"
    )

    # Other statistics
    mean_rh_annual: Optional[int] = Field(None, description="Mean annual relative humidity %")

    # Sunshine statistics (WMO: SUM)
    sunshine_total: Optional[float] = Field(
        None,
        description="Total annual sunshine hours (SUM, theoretical max ~4380h, WMO-compliant)"
    )

    # Data quality
    data_completeness_percent: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Data completeness percentage (days_with_data / 365 * 100)"
    )

    # Metadata
    created_at: datetime
    updated_at: datetime


# ============================================================================
# ENRICHED RESPONSES WITH STATION INFO (Phase 2)
# ============================================================================

class DekadalSummaryWithStation(DekadalSummaryResponse):
    """Dekadal summary enriched with station information."""
    station: StationInfo = Field(..., description="Station details")


class SeasonalSummaryWithStation(SeasonalSummaryResponse):
    """Seasonal summary enriched with station information."""
    station: StationInfo = Field(..., description="Station details")


class AnnualSummaryWithStation(AnnualSummaryResponse):
    """Annual summary enriched with station information."""
    station: StationInfo = Field(..., description="Station details")
