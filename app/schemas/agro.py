"""
Pydantic schemas for agrometeorological product API responses.

This module defines response models for:
- Growing Degree Days (GDD)
- Reference Evapotranspiration (ET₀)
- Crop water balance
- Rainy season onset/cessation
"""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class GDDResponse(BaseModel):
    """Growing Degree Days accumulation response."""

    model_config = ConfigDict(from_attributes=True)

    station_code: str = Field(..., description="Station code")
    station_name: str = Field(..., description="Station name")
    crop: str = Field(..., description="Crop type (maize, rice, or sorghum)")
    start_date: date = Field(..., description="Start date of accumulation period")
    end_date: date = Field(..., description="End date of accumulation period")
    gdd_accumulated: float = Field(..., description="Total GDD accumulated (degree-days)")
    days_count: int = Field(..., description="Number of days with data")
    average_gdd_per_day: float = Field(..., description="Average GDD per day")
    base_temp: float = Field(..., description="Base temperature for crop (°C)")
    upper_temp: Optional[float] = Field(None, description="Upper threshold temperature (°C)")
    crop_stage: Optional[str] = Field(None, description="Current growth stage based on GDD")
    days_to_maturity: Optional[int] = Field(None, description="Estimated days remaining to maturity")
    maturity_gdd: float = Field(..., description="GDD required for crop maturity")


class ET0DailyValue(BaseModel):
    """Single day ET₀ value."""

    model_config = ConfigDict(from_attributes=True)

    observation_date: date = Field(..., description="Date of observation")
    et0_mm: float = Field(..., description="Daily ET₀ (mm/day)")
    temp_max: float = Field(..., description="Maximum temperature (°C)")
    temp_min: float = Field(..., description="Minimum temperature (°C)")


class ET0Response(BaseModel):
    """Reference evapotranspiration time series response."""

    model_config = ConfigDict(from_attributes=True)

    station_code: str = Field(..., description="Station code")
    station_name: str = Field(..., description="Station name")
    latitude: float = Field(..., description="Station latitude (decimal degrees)")
    start_date: date = Field(..., description="Start date of period")
    end_date: date = Field(..., description="End date of period")
    total_et0_mm: float = Field(..., description="Total ET₀ for period (mm)")
    average_et0_mm: float = Field(..., description="Average daily ET₀ (mm/day)")
    days_count: int = Field(..., description="Number of days with data")
    daily_values: List[ET0DailyValue] = Field(..., description="Daily ET₀ time series")


class WaterBalanceDailyValue(BaseModel):
    """Single day water balance value."""

    model_config = ConfigDict(from_attributes=True)

    observation_date: date = Field(..., description="Date of observation")
    rainfall_mm: float = Field(..., description="Daily rainfall (mm)")
    et0_mm: float = Field(..., description="Daily ET₀ (mm)")
    etc_mm: float = Field(..., description="Daily crop ET (mm)")
    water_balance_mm: float = Field(..., description="Daily water balance (rainfall - ETc)")


class WaterBalanceResponse(BaseModel):
    """Crop water balance response."""

    model_config = ConfigDict(from_attributes=True)

    station_code: str = Field(..., description="Station code")
    station_name: str = Field(..., description="Station name")
    crop: str = Field(..., description="Crop type (maize, rice, or sorghum)")
    start_date: date = Field(..., description="Start date of period")
    end_date: date = Field(..., description="End date of period")
    total_rainfall_mm: float = Field(..., description="Total rainfall (mm)")
    total_et0_mm: float = Field(..., description="Total reference ET₀ (mm)")
    total_etc_mm: float = Field(..., description="Total crop evapotranspiration (mm)")
    water_balance_mm: float = Field(
        ...,
        description="Water balance: Rainfall - ETc (positive=surplus, negative=deficit)"
    )
    deficit_days: int = Field(..., description="Number of days with water deficit")
    surplus_days: int = Field(..., description="Number of days with water surplus")
    irrigation_requirement_mm: float = Field(
        ...,
        description="Total water deficit requiring irrigation (mm)"
    )
    water_stress_index: float = Field(
        ...,
        description="Water stress index: deficit as % of ETc (0-100)"
    )
    kc_avg: float = Field(..., description="Average crop coefficient used")
    daily_values: List[WaterBalanceDailyValue] = Field(..., description="Daily water balance time series")


class OnsetCessationResponse(BaseModel):
    """Rainy season onset/cessation response."""

    model_config = ConfigDict(from_attributes=True)

    station_code: str = Field(..., description="Station code")
    station_name: str = Field(..., description="Station name")
    year: int = Field(..., description="Year")
    season: str = Field(..., description="Season code (MAM, JJA, SON, DJF)")
    onset_date: Optional[date] = Field(
        None,
        description="Date when rainy season started (WMO criteria: 20mm in 3 days)"
    )
    cessation_date: Optional[date] = Field(
        None,
        description="Date when rainy season ended (< 10mm in 20 days)"
    )
    season_length_days: Optional[int] = Field(
        None,
        description="Days between onset and cessation (growing season length)"
    )
    search_window_start: Optional[date] = Field(
        None,
        description="Start of search window for onset"
    )
    search_window_end: Optional[date] = Field(
        None,
        description="End of search window for cessation"
    )
    status: str = Field(
        ...,
        description="Status: 'detected', 'pending', 'not_found', 'not_applicable', or 'no_data'"
    )
