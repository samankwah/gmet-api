"""
PDR v1 compliant endpoints.

This module implements the endpoints as specified in the Project Design Document (PDR).
These endpoints provide a more user-friendly interface aligned with the official specification.
"""

import logging
from datetime import datetime, timedelta, time, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request, status, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.dependencies.auth import get_api_key, get_api_key_optional
from app.models.api_key import APIKey
from app.schemas.weather import ObservationResponse
from app.crud.weather import station as station_crud, observation as observation_crud, daily_summary as daily_summary_crud
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1",
    tags=["Public Weather API (v1)"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not found"}
    },
)

limiter = Limiter(key_func=get_remote_address)


@router.get("/current", response_model=ObservationResponse)
@limiter.limit("100/minute")
async def get_current_weather(
    request: Request,
    location: str = Query(
        ...,
        description="Location name (e.g., 'Accra', 'Kumasi') or station code (e.g., 'DGAA')",
        examples=["Accra", "Kumasi", "DGAA"]
    ),
    db: AsyncSession = Depends(get_db),
    api_key: Optional[APIKey] = Security(get_api_key_optional),
):
    """
    Get current weather observations for a location.

    This endpoint provides the most recent weather data for a specified location.
    The location can be either a city name (e.g., 'Accra') or a station code (e.g., 'DGAA').

    **🔓 Public Endpoint:** No authentication required. API key is optional.

    **PDR Specification:** `/v1/current?location=Accra`

    **Response includes:**
    - Temperature (°C)
    - Humidity (%)
    - Wind speed (m/s)
    - Wind direction (degrees)
    - Rainfall (mm)
    - Atmospheric pressure (hPa)
    - Observation timestamp
    - Station information

    **Rate limit:** 100 requests per minute (unauthenticated)

    **Example:**
    ```
    GET /v1/current?location=Accra
    ```

    **Sample Response:**
    ```json
    {
        "id": 123,
        "station_id": 1,
        "timestamp": "2026-01-03T14:30:00Z",
        "temperature": 28.5,
        "humidity": 75.0,
        "wind_speed": 12.5,
        "wind_direction": 180.0,
        "rainfall": 0.0,
        "pressure": 1013.25,
        "created_at": "2026-01-03T14:31:00Z",
        "updated_at": "2026-01-03T14:31:00Z"
    }
    ```

    Args:
        request: FastAPI request object
        location: City name or station code
        db: Database session
        api_key: Optional API key (not required for this endpoint)

    Returns:
        ObservationResponse: Latest weather observation

    Raises:
        HTTPException: 404 if location not found or no observations available
    """
    logger.info(f"Current weather request for location: {location}")

    # Try to find station by code first (exact match)
    station = await station_crud.get_by_code(db, code=location.upper())

    # If not found by code, try to find by name (case-insensitive, database query)
    if not station:
        from sqlalchemy import or_, func
        from app.models.station import Station

        # Use database query instead of loading all stations
        result = await db.execute(
            select(Station).where(
                or_(
                    func.lower(Station.name) == location.lower(),
                    func.lower(Station.name).like(f"%{location.lower()}%")
                )
            ).limit(1)
        )
        station = result.scalar_one_or_none()

        if station:
            logger.info(f"Station found by name search: {station.name} for query '{location}'")

    if not station:
        logger.warning(f"Location not found: {location}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location '{location}' not found. Please use a valid city name or station code."
        )

    # Try to get daily summary first (preferred for current day data)
    daily = await daily_summary_crud.get_latest_for_station(db, station_id=station.id)

    # Check if daily summary is recent (within last 24 hours)
    if daily and (datetime.now(timezone.utc).date() - daily.date).days <= 1:
        logger.info(f"Current weather from daily summary for {station.name}: min={daily.temp_min}°C, max={daily.temp_max}°C")

        # Return as observation format with temp_min and temp_max fields
        # Calculate average for backward compatibility
        avg_temp = None
        if daily.temp_min is not None and daily.temp_max is not None:
            avg_temp = (daily.temp_min + daily.temp_max) / 2
        elif daily.temp_min is not None:
            avg_temp = daily.temp_min
        elif daily.temp_max is not None:
            avg_temp = daily.temp_max

        return {
            "id": daily.id,
            "station_id": daily.station_id,
            "obs_datetime": datetime.combine(daily.date, time(12, 0), tzinfo=timezone.utc),
            "temperature": avg_temp,  # For backward compatibility
            "temp_min": daily.temp_min,  # Separate min temp
            "temp_max": daily.temp_max,  # Separate max temp

            # Individual RH readings at SYNOP times
            "rh_0600": daily.rh_0600,
            "rh_0900": daily.rh_0900,
            "rh_1200": daily.rh_1200,
            "rh_1500": daily.rh_1500,

            "relative_humidity": daily.mean_rh,  # Mean RH for backward compatibility
            "wind_speed": daily.wind_speed,
            "wind_direction": None,
            "rainfall": daily.rainfall_total,
            "pressure": None,
            "created_at": daily.created_at,
            "updated_at": daily.updated_at
        }

    # Fall back to latest synoptic observation
    observation = await observation_crud.get_latest_for_station(db, station_id=station.id)

    if not observation:
        logger.warning(f"No observations found for station: {station.name} ({station.code})")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No weather observations available for '{location}'. Station: {station.name}"
        )

    logger.info(f"Current weather from synoptic observation for {station.name}: {observation.temperature}°C")
    return observation


@router.get("/historical", response_model=List[ObservationResponse])
@limiter.limit("100/minute")
async def get_historical_weather(
    request: Request,
    station: Optional[str] = Query(
        None,
        description="Station code or name",
        examples=["DGAA", "Accra"]
    ),
    start: str = Query(
        ...,
        description="Start date in YYYY-MM-DD format",
        examples=["2025-01-01"]
    ),
    end: str = Query(
        ...,
        description="End date in YYYY-MM-DD format",
        examples=["2025-12-31"]
    ),
    granularity: str = Query(
        "daily",
        description="Data granularity: 'daily' (default) returns daily summaries with min/max temps, 'synoptic' returns time-specific observations",
        examples=["daily", "synoptic"]
    ),
    param: Optional[str] = Query(
        None,
        description="Specific parameter to retrieve (e.g., 'rainfall', 'temperature')",
        examples=["rainfall", "temperature", "humidity"]
    ),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    db: AsyncSession = Depends(get_db),
    api_key: Optional[APIKey] = Security(get_api_key_optional),
):
    """
    Get historical weather data for a specified time period.

    Retrieve weather observations within a date range, optionally filtered by station
    and specific weather parameter.

    **🔓 Public Endpoint:** No authentication required. API key is optional.

    **PDR Specification:** `/v1/historical?station=Tamale&start=YYYY-MM-DD&end=YYYY-MM-DD&param=rainfall`

    **Parameters:**
    - `station` (optional): Station code or name
    - `start` (required): Start date (YYYY-MM-DD)
    - `end` (required): End date (YYYY-MM-DD)
    - `param` (optional): Specific parameter to filter (currently returns all, filter client-side)
    - `limit`: Maximum records to return (default: 1000, max: 10000)
    - `skip`: Pagination offset

    **Rate limit:** 100 requests per minute (unauthenticated)

    **Example:**
    ```
    GET /v1/historical?station=Accra&start=2025-01-01&end=2025-01-31&param=rainfall
    ```

    **Note:** The `param` parameter is informational in this version. All weather parameters
    are returned for each observation. Filter specific parameters on the client side.

    Args:
        request: FastAPI request object
        station: Optional station identifier
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        param: Optional parameter filter (informational only)
        limit: Maximum records to return
        skip: Pagination offset
        db: Database session
        api_key: Optional API key (not required for this endpoint)

    Returns:
        List[ObservationResponse]: List of historical observations

    Raises:
        HTTPException: 400 if dates are invalid, 404 if station not found
    """
    logger.info(f"Historical data request: station={station}, start={start}, end={end}, param={param}")

    # Parse and validate dates
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        logger.error(f"Invalid date format: start={start}, end={end}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Please use YYYY-MM-DD format."
        )

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before or equal to end date."
        )

    # Check if date range is too large (prevent excessive queries)
    if (end_date - start_date).days > 365:
        logger.warning(f"Date range too large: {(end_date - start_date).days} days")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range too large. Maximum range is 365 days. Please narrow your query."
        )

    # Find station if specified
    station_obj = None
    if station:
        # Try by code first
        station_obj = await station_crud.get_by_code(db, code=station.upper())

        # If not found, try by name
        if not station_obj:
            all_stations = await station_crud.get_multi(db, skip=0, limit=1000)
            for s in all_stations:
                if s.name.lower() == station.lower() or station.lower() in s.name.lower():
                    station_obj = s
                    break

        if not station_obj:
            logger.warning(f"Station not found: {station}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Station '{station}' not found."
            )

    # Get data based on granularity
    if granularity == "daily":
        # Return daily summaries (default)
        if not station_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Station parameter is required for daily granularity"
            )

        summaries = await daily_summary_crud.get_summaries_in_date_range(
            db,
            station_id=station_obj.id,
            start_date=start_date.date(),
            end_date=end_date.date(),
            skip=skip,
            limit=limit
        )
        logger.info(f"Retrieved {len(summaries)} daily summaries for {station_obj.name}")

        # Convert to observation response format with temp_min, temp_max
        result = []
        for s in summaries:
            # Calculate average temperature for backward compatibility
            avg_temp = None
            if s.temp_min is not None and s.temp_max is not None:
                avg_temp = (s.temp_min + s.temp_max) / 2
            elif s.temp_min is not None:
                avg_temp = s.temp_min
            elif s.temp_max is not None:
                avg_temp = s.temp_max

            result.append({
                "id": s.id,
                "station_id": s.station_id,
                "obs_datetime": datetime.combine(s.date, time(12, 0), tzinfo=timezone.utc),
                "temperature": avg_temp,  # For backward compatibility
                "temp_min": s.temp_min,  # NEW: Separate min temp
                "temp_max": s.temp_max,  # NEW: Separate max temp
                "relative_humidity": s.mean_rh,
                "wind_speed": s.wind_speed,
                "wind_direction": None,
                "rainfall": s.rainfall_total,
                "pressure": None,
                "created_at": s.created_at,
                "updated_at": s.updated_at
            })

        if param:
            logger.info(f"Note: Parameter filter '{param}' is informational. All parameters returned.")

        return result

    else:
        # Return synoptic observations (time-specific)
        if station_obj:
            observations = await observation_crud.get_observations_in_date_range(
                db,
                station_id=station_obj.id,
                start_date=start_date,
                end_date=end_date,
                skip=skip,
                limit=limit
            )
            logger.info(f"Retrieved {len(observations)} synoptic observations for {station_obj.name}")
        else:
            # Get all observations in date range (across all stations)
            observations = await observation_crud.get_multi(db, skip=skip, limit=limit)
            # Filter by date range
            observations = [
                obs for obs in observations
                if start_date <= obs.obs_datetime.replace(tzinfo=None) <= end_date
            ]
            logger.info(f"Retrieved {len(observations)} synoptic observations for all stations")

        if param:
            logger.info(f"Note: Parameter filter '{param}' is informational. All parameters returned.")

        return observations


@router.get("/daily-summaries/{station_code}")
@limiter.limit("100/minute")
async def get_daily_summaries(
    request: Request,
    station_code: str,
    start: str = Query(..., description="Start date YYYY-MM-DD", examples=["2024-01-01"]),
    end: str = Query(..., description="End date YYYY-MM-DD", examples=["2024-12-31"]),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    db: AsyncSession = Depends(get_db),
    api_key: Optional[APIKey] = Security(get_api_key_optional),
):
    """
    Get daily weather summaries with separate min/max temperatures.

    This endpoint provides daily aggregated weather data including:
    - Separate minimum and maximum temperatures
    - Mean relative humidity
    - Total 24-hour rainfall
    - Maximum wind gust

    **🔓 Public Endpoint:** No authentication required. API key is optional.

    **Example:**
    ```
    GET /v1/daily-summaries/23024TEM?start=2024-01-01&end=2024-12-31
    ```

    **Response includes temp_min and temp_max fields:**
    ```json
    [
        {
            "id": 1,
            "station_id": 1,
            "date": "2024-01-01",
            "temp_max": 32.8,
            "temp_min": 26.5,
            "rainfall_total": 0.0,
            "mean_rh": 72
        }
    ]
    ```

    Args:
        request: FastAPI request object
        station_code: Station code (e.g., '23024TEM', '23016ACC')
        start: Start date in YYYY-MM-DD format
        end: End date in YYYY-MM-DD format
        limit: Maximum records to return
        skip: Number of records to skip
        db: Database session
        api_key: Optional API key (not required for this endpoint)

    Returns:
        List of daily summary records

    Raises:
        HTTPException: 400 if dates invalid, 404 if station not found
    """
    logger.info(f"Daily summaries request: station={station_code}, start={start}, end={end}")

    # Find station
    station = await station_crud.get_by_code(db, code=station_code.upper())
    if not station:
        # Try partial match
        all_stations = await station_crud.get_multi(db, skip=0, limit=1000)
        for s in all_stations:
            if station_code.lower() in s.name.lower() or station_code.lower() in s.code.lower():
                station = s
                break

        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Station '{station_code}' not found"
            )

    # Parse dates
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Please use YYYY-MM-DD format."
        )

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before or equal to end date."
        )

    # Get daily summaries
    summaries = await daily_summary_crud.get_summaries_in_date_range(
        db,
        station_id=station.id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )

    logger.info(f"Retrieved {len(summaries)} daily summaries for {station.name}")

    return summaries


# TODO [Phase 2 - Forecast Integration]:
# - Integrate with GMet forecast models or external forecast API
# - Implement forecast data storage and caching strategy
# - Add forecast validation and quality control
# - Consider integration with Clidata/Climsoft for historical forecast verification
@router.get("/forecast/daily")
@limiter.limit("100/minute")
async def get_daily_forecast(
    request: Request,
    location: str = Query(
        ...,
        description="Location name or station code",
        examples=["Accra", "Kumasi"]
    ),
    days: int = Query(
        7,
        ge=1,
        le=10,
        description="Number of forecast days (1-10)"
    ),
    api_key: APIKey = Security(get_api_key),
):
    """
    Get daily weather forecast (Placeholder - Phase 2).

    This endpoint will provide daily weather forecasts for up to 10 days.

    **PDR Specification:** `/v1/forecast/daily?location=Kumasi&days=7`

    **Status:** Not yet implemented (planned for Phase 2)

    This endpoint requires integration with GMet's forecast models and
    is scheduled for implementation in Phase 2 of the project.

    **Future Response Format:**
    ```json
    {
        "location": "Kumasi",
        "forecasts": [
            {
                "date": "2026-01-04",
                "temperature_max": 32.0,
                "temperature_min": 22.0,
                "conditions": "Partly cloudy",
                "rainfall_probability": 30,
                "wind_speed": 10.0
            }
        ]
    }
    ```

    Args:
        request: FastAPI request object
        location: City name or station code
        days: Number of forecast days (1-10)
        api_key: Valid API key

    Returns:
        NotImplementedError: This feature is planned for Phase 2

    Raises:
        HTTPException: 501 Not Implemented
    """
    logger.warning(f"Forecast endpoint called (not implemented): location={location}, days={days}")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "message": "Daily forecast endpoint is not yet implemented",
            "status": "planned",
            "phase": 2,
            "note": "This feature requires integration with GMet forecast models",
            "expected": "Q2 2026"
        }
    )
