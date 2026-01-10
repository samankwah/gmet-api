"""
Climate products router - WMO-compliant climate data endpoints.

This module provides endpoints for Ghana Meteorological Agency climate products:
- Phase 1: Daily weather products, weekly summaries, monthly climate summaries

All products follow WMO guidelines for climate data aggregation and are suitable
for international data exchange and WMO reporting.
"""

from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request, status, Security
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.dependencies.auth import get_api_key
from app.models.api_key import APIKey
from app.schemas.products import (
    DailyWeatherProductResponse,
    WeeklySummaryResponse,
    MonthlySummaryResponse,
    DekadalSummaryResponse,
    SeasonalSummaryResponse,
    AnnualSummaryResponse,
)
from app.crud import products as products_crud
from app.crud.weather import station as station_crud, daily_summary as daily_summary_crud
from app.utils.logging_config import get_logger
from app.utils.aggregation import get_iso_week

logger = get_logger(__name__)

router = APIRouter(
    prefix="/products",
    tags=["Climate Products"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing API key"},
        404: {"description": "Resource not found"},
        400: {"description": "Bad request - Invalid parameters"}
    },
)

limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# DAILY WEATHER PRODUCTS
# ============================================================================

@router.get("/daily", response_model=List[DailyWeatherProductResponse])
@limiter.limit("100/minute")
async def get_daily_weather_products(
    request: Request,
    station_code: str = Query(
        ...,
        description="Station code (e.g., '23024TEM', 'DGAA')",
        examples=["23024TEM"]
    ),
    start_date: date = Query(
        ...,
        description="Start date (YYYY-MM-DD)",
        examples=["2024-01-01"]
    ),
    end_date: date = Query(
        ...,
        description="End date (YYYY-MM-DD)",
        examples=["2024-01-31"]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Get daily weather products for operational summaries.

    Returns daily weather summaries including:
    - Maximum and minimum temperatures with timestamps
    - Total 24-hour rainfall
    - Mean relative humidity (and individual SYNOP readings)
    - Mean wind speed
    - Total sunshine hours

    **Use case**: Public daily weather bulletins, operational summaries

    **Data source**: Existing daily_summaries table (no computation required)

    **WMO compliance**: Daily aggregations follow GMet operational standards

    **Example request**:
    ```
    GET /api/v1/products/daily?station_code=23024TEM&start_date=2024-01-01&end_date=2024-01-31
    ```

    **Rate limit**: 100 requests per minute

    Args:
        request: FastAPI request object
        station_code: Station code
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        db: Database session
        api_key: Valid API key

    Returns:
        List[DailyWeatherProductResponse]: Daily weather summaries

    Raises:
        HTTPException: 404 if station not found, 400 if date range invalid
    """
    logger.info(f"Daily products request: station={station_code}, start={start_date}, end={end_date}")

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )

    # Check date range is not too large (max 1 year)
    days_diff = (end_date - start_date).days
    if days_diff > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range too large. Maximum 365 days allowed."
        )

    # Find station
    station = await station_crud.get_by_code(db, code=station_code.upper())
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_code}' not found"
        )

    # Get daily summaries (no computation needed - already in database)
    summaries = await daily_summary_crud.get_summaries_in_date_range(
        db,
        station_id=station.id,
        start_date=start_date,
        end_date=end_date,
        skip=0,
        limit=1000
    )

    logger.info(f"Retrieved {len(summaries)} daily summaries for {station.name}")

    # Calculate mean temperature for each day
    result = []
    for s in summaries:
        temp_mean = None
        if s.temp_min is not None and s.temp_max is not None:
            temp_mean = (s.temp_min + s.temp_max) / 2

        result.append({
            "id": s.id,
            "station_id": s.station_id,
            "date": s.date,
            "temp_max": s.temp_max,
            "temp_min": s.temp_min,
            "temp_mean": temp_mean,
            "rainfall_total": s.rainfall_total,
            "mean_rh": s.mean_rh,
            "rh_0600": s.rh_0600,
            "rh_0900": s.rh_0900,
            "rh_1200": s.rh_1200,
            "rh_1500": s.rh_1500,
            "wind_speed": s.wind_speed,
            "sunshine_hours": s.sunshine_hours,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        })

    return result


# ============================================================================
# WEEKLY SUMMARIES
# ============================================================================

@router.get("/weekly", response_model=List[WeeklySummaryResponse])
@limiter.limit("100/minute")
async def get_weekly_summaries(
    request: Request,
    station_code: str = Query(
        ...,
        description="Station code (e.g., '23024TEM', 'DGAA')",
        examples=["23016ACC"]
    ),
    year: int = Query(
        ...,
        description="ISO year",
        ge=1960,
        le=2100,
        examples=[2024]
    ),
    week_number: Optional[int] = Query(
        None,
        description="ISO week number (1-53). If omitted, returns all weeks for the year.",
        ge=1,
        le=53,
        examples=[20]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Get weekly weather summaries for media briefings and agriculture monitoring.

    Returns ISO 8601 week summaries (Monday start, weeks 1-53) with:
    - Total weekly rainfall and wet days count
    - Mean and absolute temperature extremes
    - Mean relative humidity and wind speed
    - Total sunshine hours

    **Use case**: Media briefings, agriculture monitoring, short-term analysis

    **WMO compliance**:
    - Rainfall/sunshine: SUMMED (never averaged)
    - Temperatures: MEAN of daily Tmax/Tmin
    - Requires >= 5 days data (71% completeness)

    **Hybrid compute**: Recent years pre-computed, historical on-demand

    **Example requests**:
    ```
    # Get specific week
    GET /api/v1/products/weekly?station_code=23016ACC&year=2024&week_number=20

    # Get all weeks for a year
    GET /api/v1/products/weekly?station_code=23016ACC&year=2024
    ```

    **Rate limit**: 100 requests per minute

    Args:
        request: FastAPI request object
        station_code: Station code
        year: ISO year
        week_number: Optional ISO week number (1-53)
        db: Database session
        api_key: Valid API key

    Returns:
        List[WeeklySummaryResponse]: Weekly summaries

    Raises:
        HTTPException: 404 if station not found or no data available
    """
    logger.info(f"Weekly summaries request: station={station_code}, year={year}, week={week_number}")

    # Find station
    station = await station_crud.get_by_code(db, code=station_code.upper())
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_code}' not found"
        )

    # Get weekly summaries (lazy computation)
    if week_number:
        # Get specific week
        summary = await products_crud.weekly_summary.get_or_compute(
            db,
            station_id=station.id,
            year=year,
            week_number=week_number
        )

        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data available for week {week_number} of {year}. Insufficient daily observations (requires >= 5 days)."
            )

        summaries = [summary]
    else:
        # Get all weeks for the year
        summaries = await products_crud.weekly_summary.get_for_year(
            db,
            station_id=station.id,
            year=year
        )

        if not summaries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No weekly data available for {year}"
            )

    logger.info(f"Retrieved {len(summaries)} weekly summaries for {station.name}")
    return summaries


# ============================================================================
# MONTHLY CLIMATE SUMMARIES
# ============================================================================

@router.get("/monthly", response_model=List[MonthlySummaryResponse])
@limiter.limit("100/minute")
async def get_monthly_summaries(
    request: Request,
    station_code: str = Query(
        ...,
        description="Station code (e.g., '23024TEM', 'DGAA')",
        examples=["17009KSI"]
    ),
    year: int = Query(
        ...,
        description="Calendar year",
        ge=1960,
        le=2100,
        examples=[2024]
    ),
    month: Optional[int] = Query(
        None,
        description="Month (1-12). If omitted, returns all months for the year.",
        ge=1,
        le=12,
        examples=[5]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Get monthly climate summaries for bulletins, research, and policy.

    Returns monthly aggregations with:
    - Total rainfall, anomaly vs 1991-2020 normal, rainfall days
    - Mean and extreme temperatures with anomalies
    - Mean relative humidity and wind speed
    - Total sunshine hours
    - Data completeness percentage

    **Use case**: Climate bulletins, research, policy decisions, WMO reporting

    **WMO compliance**:
    - Rainfall/sunshine: SUMMED (never averaged)
    - Temperatures: MEAN of daily Tmax/Tmin
    - Requires >= 21 days data (70% completeness)

    **Anomalies**: Calculated vs 1991-2020 climate normals (if available)

    **Hybrid compute**: Recent years pre-computed, historical on-demand

    **Example requests**:
    ```
    # Get specific month
    GET /api/v1/products/monthly?station_code=17009KSI&year=2024&month=5

    # Get all months for a year
    GET /api/v1/products/monthly?station_code=17009KSI&year=2024
    ```

    **Rate limit**: 100 requests per minute

    Args:
        request: FastAPI request object
        station_code: Station code
        year: Calendar year
        month: Optional month (1-12)
        db: Database session
        api_key: Valid API key

    Returns:
        List[MonthlySummaryResponse]: Monthly climate summaries

    Raises:
        HTTPException: 404 if station not found or no data available
    """
    logger.info(f"Monthly summaries request: station={station_code}, year={year}, month={month}")

    # Find station
    station = await station_crud.get_by_code(db, code=station_code.upper())
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_code}' not found"
        )

    # Get monthly summaries (lazy computation)
    if month:
        # Get specific month
        summary = await products_crud.monthly_summary.get_or_compute(
            db,
            station_id=station.id,
            year=year,
            month=month
        )

        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data available for {year}-{month:02d}. Insufficient daily observations (requires >= 70% completeness)."
            )

        summaries = [summary]
    else:
        # Get all months for the year
        summaries = await products_crud.monthly_summary.get_for_year(
            db,
            station_id=station.id,
            year=year
        )

        if not summaries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No monthly data available for {year}"
            )

    logger.info(f"Retrieved {len(summaries)} monthly summaries for {station.name}")
    return summaries


# ============================================================================
# DEKADAL SUMMARIES (Phase 2)
# ============================================================================

@router.get("/dekad", response_model=List[DekadalSummaryResponse])
@limiter.limit("100/minute")
async def get_dekadal_summaries(
    request: Request,
    station_code: str = Query(
        ...,
        description="Station code (e.g., '23024TEM', 'DGAA')",
        examples=["07006TLE"]
    ),
    year: int = Query(
        ...,
        description="Calendar year",
        ge=1960,
        le=2100,
        examples=[2024]
    ),
    month: int = Query(
        ...,
        description="Month (1-12)",
        ge=1,
        le=12,
        examples=[5]
    ),
    dekad: Optional[int] = Query(
        None,
        description="Dekad number (1, 2, or 3). If omitted, returns all 3 dekads for the month.",
        ge=1,
        le=3,
        examples=[2]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Get 10-day (dekadal) climate summaries for agrometeorological monitoring.

    **Dekad definitions** (WMO standard - NOT arbitrary 10-day windows):
    - Dekad 1: Days 1-10 of the month
    - Dekad 2: Days 11-20 of the month
    - Dekad 3: Days 21 to end of month (28/29/30/31)

    Returns dekadal aggregations with:
    - Total rainfall and rainy days
    - Mean and extreme temperatures
    - Mean relative humidity
    - Total sunshine hours

    **Use case**: Agrometeorological bulletins, crop monitoring, irrigation planning

    **WMO compliance**:
    - Rainfall/sunshine: SUMMED (never averaged)
    - Temperatures: MEAN of daily Tmax/Tmin
    - Requires >= 7 days data (70% completeness)

    **Example requests**:
    ```
    # Get specific dekad
    GET /api/v1/products/dekad?station_code=07006TLE&year=2024&month=5&dekad=2

    # Get all dekads for a month
    GET /api/v1/products/dekad?station_code=07006TLE&year=2024&month=5
    ```

    **Rate limit**: 100 requests per minute
    """
    logger.info(f"Dekadal summaries request: station={station_code}, year={year}, month={month}, dekad={dekad}")

    # Find station
    station = await station_crud.get_by_code(db, code=station_code.upper())
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_code}' not found"
        )

    # Get dekadal summaries
    if dekad:
        # Get specific dekad
        summary = await products_crud.dekadal_summary.get_or_compute(
            db,
            station_id=station.id,
            year=year,
            month=month,
            dekad=dekad
        )

        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data available for dekad {dekad} of {year}-{month:02d}. Insufficient daily observations (requires >= 7 days)."
            )

        summaries = [summary]
    else:
        # Get all dekads for the month
        summaries = await products_crud.dekadal_summary.get_for_month(
            db,
            station_id=station.id,
            year=year,
            month=month
        )

        if not summaries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No dekadal data available for {year}-{month:02d}"
            )

    logger.info(f"Retrieved {len(summaries)} dekadal summaries for {station.name}")
    return summaries


# ============================================================================
# SEASONAL SUMMARIES (Phase 2)
# ============================================================================

@router.get("/seasonal", response_model=List[SeasonalSummaryResponse])
@limiter.limit("100/minute")
async def get_seasonal_summaries(
    request: Request,
    station_code: str = Query(
        ...,
        description="Station code (e.g., '23024TEM', 'DGAA')",
        examples=["04003NAV"]
    ),
    year: int = Query(
        ...,
        description="Calendar year (for DJF, this is the December year)",
        ge=1960,
        le=2100,
        examples=[2024]
    ),
    season: Optional[str] = Query(
        None,
        description="Season code: MAM, JJA, SON, or DJF. If omitted, returns all 4 seasons for the year.",
        pattern="^(MAM|JJA|SON|DJF)$",
        examples=["MAM"]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Get seasonal climate summaries for agricultural planning and forecasting.

    **Ghana-specific seasons** (following West African climate patterns):
    - **MAM** (March-May): Major rainy season - **primary planting period**
    - **JJA** (June-August): Minor rainy season - important for southern Ghana
    - **SON** (September-November): Post-rainy/transition - **harvest period**
    - **DJF** (December-February): Dry season/Harmattan - lowest rainfall

    Returns seasonal aggregations with:
    - Total rainfall, anomaly, and rainy days
    - **Onset/cessation dates** (CRITICAL for planting/harvest decisions)
    - **Season length** (days between onset and cessation)
    - Dry spell analysis (count and maximum duration)
    - Mean and extreme temperatures, hot days count
    - Mean relative humidity and total sunshine

    **Use case**: Seasonal forecasts, agricultural planning, policy decisions

    **WMO compliance**:
    - Rainfall/sunshine: SUMMED (never averaged)
    - Temperatures: MEAN of daily Tmax/Tmin
    - Requires >= 63 days data (70% completeness)

    **Agricultural timing indicators**:
    - Onset: 20mm cumulative in 3 days, no 7-day dry spell in next 20 days
    - Cessation: Last rainy day before < 10mm in 20 days
    - **Critical for planting and harvest decisions**

    **Example requests**:
    ```
    # Get specific season
    GET /api/v1/products/seasonal?station_code=04003NAV&year=2024&season=MAM

    # Get all seasons for a year
    GET /api/v1/products/seasonal?station_code=04003NAV&year=2024
    ```

    **Rate limit**: 100 requests per minute
    """
    logger.info(f"Seasonal summaries request: station={station_code}, year={year}, season={season}")

    # Find station
    station = await station_crud.get_by_code(db, code=station_code.upper())
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_code}' not found"
        )

    # Get seasonal summaries
    if season:
        # Get specific season
        summary = await products_crud.seasonal_summary.get_or_compute(
            db,
            station_id=station.id,
            year=year,
            season=season.upper()
        )

        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data available for {season} {year}. Insufficient daily observations (requires >= 70% completeness)."
            )

        summaries = [summary]
    else:
        # Get all seasons for the year
        summaries = await products_crud.seasonal_summary.get_for_year(
            db,
            station_id=station.id,
            year=year
        )

        if not summaries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No seasonal data available for {year}"
            )

    logger.info(f"Retrieved {len(summaries)} seasonal summaries for {station.name}")
    return summaries


# ============================================================================
# ANNUAL SUMMARIES (Phase 2)
# ============================================================================

@router.get("/annual", response_model=List[AnnualSummaryResponse])
@limiter.limit("100/minute")
async def get_annual_summaries(
    request: Request,
    station_code: str = Query(
        ...,
        description="Station code (e.g., '23024TEM', 'DGAA')",
        examples=["23024TEM"]
    ),
    start_year: int = Query(
        ...,
        description="Start year (inclusive)",
        ge=1960,
        le=2100,
        examples=[2020]
    ),
    end_year: int = Query(
        ...,
        description="End year (inclusive)",
        ge=1960,
        le=2100,
        examples=[2024]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Get annual climate summaries for reports, WMO submissions, and trend analysis.

    Returns comprehensive annual aggregations with:
    - Total rainfall, anomaly, rainfall days, and maximum daily rainfall (with date)
    - Absolute temperature extremes (with dates)
    - Mean annual temperature and anomaly
    - Extreme event counts (hot days, very hot days, heavy rain days)
    - Mean annual relative humidity and total sunshine
    - Data completeness percentage

    **Use case**: Climate reports, WMO submissions, long-term trend analysis

    **WMO compliance**:
    - Rainfall/sunshine: SUMMED (never averaged)
    - Temperatures: MEAN of daily Tmax/Tmin
    - Requires >= 292 days data (80% completeness)

    **Extreme event thresholds**:
    - Hot days: Tmax > 35°C
    - Very hot days: Tmax > 40°C
    - Heavy rain days: > 50mm

    **Multi-year queries**: Request up to 30 years of data for trend analysis

    **Example requests**:
    ```
    # Get single year
    GET /api/v1/products/annual?station_code=23024TEM&start_year=2024&end_year=2024

    # Get 5-year period for trend analysis
    GET /api/v1/products/annual?station_code=23024TEM&start_year=2020&end_year=2024
    ```

    **Rate limit**: 100 requests per minute
    """
    logger.info(f"Annual summaries request: station={station_code}, years={start_year}-{end_year}")

    # Validate year range
    if end_year < start_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_year must be greater than or equal to start_year"
        )

    if end_year - start_year > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum year range is 30 years"
        )

    # Find station
    station = await station_crud.get_by_code(db, code=station_code.upper())
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station '{station_code}' not found"
        )

    # Get annual summaries
    summaries = await products_crud.annual_summary.get_for_range(
        db,
        station_id=station.id,
        start_year=start_year,
        end_year=end_year
    )

    if not summaries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No annual data available for {start_year}-{end_year}"
        )

    logger.info(f"Retrieved {len(summaries)} annual summaries for {station.name}")
    return summaries
