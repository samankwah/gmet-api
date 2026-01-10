"""
Agrometeorological products router - Agricultural decision support endpoints.

This module provides endpoints for Ghana Meteorological Agency agrometeorological products:
- Growing Degree Days (GDD) for crop development tracking
- Reference Evapotranspiration (ET₀) for irrigation planning
- Crop water balance for water stress monitoring
- Rainy season onset/cessation for planting advisories

All products follow WMO agricultural meteorology guidelines (GAMP).
"""

from datetime import date
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, Request, status, Security
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.dependencies.auth import get_api_key
from app.models.api_key import APIKey
from app.schemas.agro import (
    GDDResponse,
    ET0Response,
    WaterBalanceResponse,
    OnsetCessationResponse,
    ET0DailyValue,
    WaterBalanceDailyValue,
)
from app.crud.weather import station as station_crud
from app.utils import agro
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/agro",
    tags=["Agrometeorological Products"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing API key"},
        404: {"description": "Resource not found"},
        400: {"description": "Bad request - Invalid parameters"}
    },
)

limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# GROWING DEGREE DAYS (GDD)
# ============================================================================

@router.get("/gdd", response_model=GDDResponse)
@limiter.limit("100/minute")
async def get_growing_degree_days(
    request: Request,
    station_code: str = Query(
        ...,
        description="Station code (e.g., '04003NAV', '17009KSI')",
        examples=["04003NAV"]
    ),
    start_date: date = Query(
        ...,
        description="Start date - planting date (YYYY-MM-DD)",
        examples=["2024-03-15"]
    ),
    end_date: date = Query(
        ...,
        description="End date - current or harvest date (YYYY-MM-DD)",
        examples=["2024-06-30"]
    ),
    crop: str = Query(
        ...,
        description="Crop type: 'maize', 'rice', or 'sorghum'",
        examples=["maize"]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Calculate Growing Degree Days (GDD) accumulation for a crop.

    GDD tracks thermal time accumulation for crop development. Used to:
    - Predict crop growth stages (emergence, tasseling, flowering, maturity)
    - Estimate days to maturity
    - Plan harvest timing

    **Supported crops (Ghana-calibrated parameters):**
    - `maize`: Base 10°C, Upper 30°C, Maturity ~1400 GDD (90-110 day varieties)
    - `rice`: Base 10°C, Upper 35°C, Maturity ~2000 GDD (120-150 day varieties)
    - `sorghum`: Base 8°C, Upper 35°C, Maturity ~1600 GDD (100-130 day varieties)

    **Calculation method:**
    Modified GDD = ((Tmax_adj + Tmin_adj) / 2) - Tbase

    Where temperatures are capped at upper/lower thresholds.

    **Use case**: Crop stage tracking, maturity prediction, extension advisory

    **Example request**:
    ```
    GET /api/v1/agro/gdd?station_code=04003NAV&start_date=2024-03-15&end_date=2024-06-30&crop=maize
    ```

    **Example interpretation**:
    - GDD accumulated: 876 (out of 1400 for maturity)
    - Crop stage: Tasseling
    - Days to maturity: ~46 days

    **Rate limit**: 100 requests per minute

    Args:
        request: FastAPI request object
        station_code: Station code
        start_date: Planting date
        end_date: Current or harvest date
        crop: Crop type
        db: Database session
        api_key: API key for authentication

    Returns:
        GDDResponse with accumulation data and crop stage

    Raises:
        HTTPException: 404 if station not found, 400 if invalid crop
    """
    # Validate crop type
    if crop not in ['maize', 'rice', 'sorghum']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid crop type: {crop}. Must be 'maize', 'rice', or 'sorghum'"
        )

    # Get station
    station = await station_crud.get_by_code(db, code=station_code)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station not found: {station_code}"
        )

    # Compute GDD
    gdd_data = await agro.compute_gdd_accumulation(
        db, station.id, start_date, end_date, crop
    )

    if not gdd_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No temperature data available for {station_code} in the specified period"
        )

    return GDDResponse(
        station_code=station.code,
        station_name=station.name,
        **gdd_data
    )


# ============================================================================
# REFERENCE EVAPOTRANSPIRATION (ET₀)
# ============================================================================

@router.get("/et0", response_model=ET0Response)
@limiter.limit("100/minute")
async def get_reference_evapotranspiration(
    request: Request,
    station_code: str = Query(
        ...,
        description="Station code (e.g., '23024TEM', '04003NAV')",
        examples=["23024TEM"]
    ),
    start_date: date = Query(
        ...,
        description="Start date (YYYY-MM-DD)",
        examples=["2024-04-01"]
    ),
    end_date: date = Query(
        ...,
        description="End date (YYYY-MM-DD)",
        examples=["2024-06-30"]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Calculate reference evapotranspiration (ET₀) using Hargreaves method.

    ET₀ represents atmospheric water demand for a reference grass surface.
    Used for:
    - Irrigation scheduling
    - Crop water requirement calculations
    - Drought monitoring

    **Calculation method**: Hargreaves-Samani (1985)

    ET₀ = 0.0023 × (Tmean + 17.8) × (Tmax - Tmin)^0.5 × Ra

    Where:
    - Tmean = (Tmax + Tmin) / 2
    - Ra = Extraterrestrial radiation (from latitude and day of year)

    **Advantages**:
    - Only requires temperature data (Tmax, Tmin)
    - Suitable for Ghana where radiation data is sparse
    - Accuracy: ±10-15% vs Penman-Monteith for tropical regions

    **Typical ET₀ values for Ghana**:
    - Dry season (DJF): 4-6 mm/day
    - Rainy season (MAM/JJA): 3-5 mm/day
    - Annual: 1200-1800 mm

    **Use case**: Irrigation planning, water balance calculations

    **Example request**:
    ```
    GET /api/v1/agro/et0?station_code=23024TEM&start_date=2024-04-01&end_date=2024-06-30
    ```

    **Rate limit**: 100 requests per minute

    Args:
        request: FastAPI request object
        station_code: Station code
        start_date: Start date
        end_date: End date
        db: Database session
        api_key: API key for authentication

    Returns:
        ET0Response with daily ET₀ time series

    Raises:
        HTTPException: 404 if station not found or no data available
    """
    # Get station
    station = await station_crud.get_by_code(db, code=station_code)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station not found: {station_code}"
        )

    # Check latitude availability
    if station.latitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Station {station_code} does not have latitude data (required for ET₀ calculation)"
        )

    # Compute ET₀ series
    et0_series = await agro.compute_et0_series(
        db, station.id, start_date, end_date
    )

    if not et0_series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No temperature data available for {station_code} in the specified period"
        )

    # Calculate totals
    total_et0 = sum(item['et0_mm'] for item in et0_series)
    average_et0 = total_et0 / len(et0_series)

    return ET0Response(
        station_code=station.code,
        station_name=station.name,
        latitude=station.latitude,
        start_date=start_date,
        end_date=end_date,
        total_et0_mm=round(total_et0, 1),
        average_et0_mm=round(average_et0, 2),
        days_count=len(et0_series),
        daily_values=[ET0DailyValue(**item) for item in et0_series]
    )


# ============================================================================
# CROP WATER BALANCE
# ============================================================================

@router.get("/water-balance", response_model=WaterBalanceResponse)
@limiter.limit("100/minute")
async def get_crop_water_balance(
    request: Request,
    station_code: str = Query(
        ...,
        description="Station code (e.g., '04003NAV', '17009KSI')",
        examples=["04003NAV"]
    ),
    start_date: date = Query(
        ...,
        description="Start date - planting date (YYYY-MM-DD)",
        examples=["2024-03-15"]
    ),
    end_date: date = Query(
        ...,
        description="End date - current or harvest date (YYYY-MM-DD)",
        examples=["2024-06-30"]
    ),
    crop: str = Query(
        ...,
        description="Crop type: 'maize', 'rice', or 'sorghum'",
        examples=["maize"]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Calculate crop water balance for irrigation planning.

    Water balance equation:
    ΔS = P - ETc

    Where:
    - P = Precipitation (rainfall)
    - ETc = Crop evapotranspiration (ET₀ × Kc)
    - Kc = Crop coefficient (varies by crop and growth stage)

    **Water balance interpretation**:
    - Positive (+): Water surplus (no irrigation needed)
    - Negative (-): Water deficit (irrigation required)

    **Crop coefficients (Kc) - average values**:
    - Maize: 0.3-1.2 (varies by stage)
    - Rice: 1.0-1.2 (flooded conditions)
    - Sorghum: 0.3-1.0 (varies by stage)

    **Water stress index**:
    - 0-25%: No stress
    - 25-50%: Moderate stress (yield impact possible)
    - 50-75%: High stress (significant yield loss)
    - >75%: Severe stress (crop failure risk)

    **Use case**: Irrigation scheduling, drought monitoring, yield prediction

    **Example request**:
    ```
    GET /api/v1/agro/water-balance?station_code=04003NAV&start_date=2024-03-15&end_date=2024-06-30&crop=maize
    ```

    **Example interpretation**:
    - Total rainfall: 245mm
    - Total ETc: 463mm
    - Water deficit: -218mm (irrigation required)
    - Water stress index: 47% (moderate to high stress)

    **Rate limit**: 100 requests per minute

    Args:
        request: FastAPI request object
        station_code: Station code
        start_date: Planting date
        end_date: Current or harvest date
        crop: Crop type
        db: Database session
        api_key: API key for authentication

    Returns:
        WaterBalanceResponse with water balance data

    Raises:
        HTTPException: 404 if station not found, 400 if invalid crop
    """
    # Validate crop type
    if crop not in ['maize', 'rice', 'sorghum']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid crop type: {crop}. Must be 'maize', 'rice', or 'sorghum'"
        )

    # Get station
    station = await station_crud.get_by_code(db, code=station_code)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station not found: {station_code}"
        )

    # Check latitude availability
    if station.latitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Station {station_code} does not have latitude data (required for water balance calculation)"
        )

    # Compute water balance
    balance_data = await agro.compute_water_balance(
        db, station.id, start_date, end_date, crop
    )

    if not balance_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data available for {station_code} in the specified period"
        )

    return WaterBalanceResponse(
        station_code=station.code,
        station_name=station.name,
        **balance_data
    )


# ============================================================================
# RAINY SEASON ONSET/CESSATION
# ============================================================================

@router.get("/onset-cessation", response_model=OnsetCessationResponse)
@limiter.limit("100/minute")
async def get_onset_cessation(
    request: Request,
    station_code: str = Query(
        ...,
        description="Station code (e.g., '04003NAV', '17009KSI')",
        examples=["04003NAV"]
    ),
    year: int = Query(
        ...,
        description="Year",
        examples=[2024],
        ge=1900,
        le=2100
    ),
    season: str = Query(
        ...,
        description="Season code: 'MAM', 'JJA', 'SON', or 'DJF'",
        examples=["MAM"]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Detect rainy season onset and cessation dates.

    **WMO Onset Definition**:
    First occurrence where:
    1. Cumulative rainfall >= 20mm in 3 consecutive days
    2. AND no dry spell >= 7 days in the following 20 days

    **WMO Cessation Definition**:
    Last rainy day before a period where:
    - Cumulative rainfall < 10mm in 20 consecutive days

    **Ghana Climate Seasons**:
    - **MAM** (March-April-May): Major rainy season - PRIMARY planting period
      - Onset search: March 1 - April 30
      - Typical onset: Mid-March to early April
    - **JJA** (June-July-August): Minor rainy season
      - Onset search: June 1 - July 15
      - Typical onset: Early to mid-June
    - **SON** (September-October-November): Post-rainy/transition - harvest period
    - **DJF** (December-January-February): Dry season/Harmattan

    **Agricultural importance**:
    - Onset date → Optimal planting window (onset + 0-7 days)
    - Season length → Suitable crop variety selection
    - Cessation date → Harvest planning

    **Status values**:
    - `detected`: Both onset and cessation found
    - `pending`: Onset found, but season hasn't ended
    - `not_found`: No valid onset detected
    - `not_applicable`: Dry seasons (SON, DJF)
    - `no_data`: Insufficient rainfall data

    **Use case**: Planting advisories, crop variety selection, food security monitoring

    **Example request**:
    ```
    GET /api/v1/agro/onset-cessation?station_code=04003NAV&year=2024&season=MAM
    ```

    **Example interpretation** (MAM 2024):
    - Onset: March 18, 2024
    - Cessation: May 28, 2024
    - Season length: 71 days
    - Planting window: March 18-25 (safe for 90-day maize varieties)

    **Rate limit**: 100 requests per minute

    Args:
        request: FastAPI request object
        station_code: Station code
        year: Year
        season: Season code
        db: Database session
        api_key: API key for authentication

    Returns:
        OnsetCessationResponse with onset/cessation dates

    Raises:
        HTTPException: 404 if station not found, 400 if invalid season
    """
    # Validate season
    if season not in ['MAM', 'JJA', 'SON', 'DJF']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid season: {season}. Must be 'MAM', 'JJA', 'SON', or 'DJF'"
        )

    # Get station
    station = await station_crud.get_by_code(db, code=station_code)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station not found: {station_code}"
        )

    # Compute onset/cessation
    onset_data = await agro.compute_onset_cessation_for_season(
        db, station.id, year, season
    )

    return OnsetCessationResponse(
        station_code=station.code,
        station_name=station.name,
        **onset_data
    )
