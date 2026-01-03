"""
PDR v1 compliant endpoints.

This module implements the endpoints as specified in the Project Design Document (PDR).
These endpoints provide a more user-friendly interface aligned with the official specification.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.dependencies.auth import validate_api_key
from app.schemas.weather import ObservationResponse
from app.crud.weather import station as station_crud, observation as observation_crud
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1",
    tags=["PDR v1 - Weather Data"],
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
    api_key: str = Depends(validate_api_key),
):
    """
    Get current weather observations for a location.

    This endpoint provides the most recent weather data for a specified location.
    The location can be either a city name (e.g., 'Accra') or a station code (e.g., 'DGAA').

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

    **Rate limit:** 100 requests per minute

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
        api_key: Valid API key

    Returns:
        ObservationResponse: Latest weather observation

    Raises:
        HTTPException: 404 if location not found or no observations available
    """
    logger.info(f"Current weather request for location: {location}")

    # Try to find station by code first (exact match)
    station = await station_crud.get_by_code(db, code=location.upper())

    # If not found by code, try to find by name (case-insensitive)
    if not station:
        # Get all stations and search by name
        all_stations = await station_crud.get_multi(db, skip=0, limit=1000)
        for s in all_stations:
            if s.name.lower() == location.lower():
                station = s
                break

        # If still not found, try partial match on name
        if not station:
            for s in all_stations:
                if location.lower() in s.name.lower():
                    station = s
                    logger.info(f"Partial match found: {s.name} for query '{location}'")
                    break

    if not station:
        logger.warning(f"Location not found: {location}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location '{location}' not found. Please use a valid city name or station code."
        )

    # Get the latest observation for this station
    observation = await observation_crud.get_latest_for_station(db, station_id=station.id)

    if not observation:
        logger.warning(f"No observations found for station: {station.name} ({station.code})")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No weather observations available for '{location}'. Station: {station.name}"
        )

    logger.info(f"Current weather retrieved for {station.name}: {observation.temperature}°C")
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
    param: Optional[str] = Query(
        None,
        description="Specific parameter to retrieve (e.g., 'rainfall', 'temperature')",
        examples=["rainfall", "temperature", "humidity"]
    ),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(validate_api_key),
):
    """
    Get historical weather data for a specified time period.

    Retrieve weather observations within a date range, optionally filtered by station
    and specific weather parameter.

    **PDR Specification:** `/v1/historical?station=Tamale&start=YYYY-MM-DD&end=YYYY-MM-DD&param=rainfall`

    **Parameters:**
    - `station` (optional): Station code or name
    - `start` (required): Start date (YYYY-MM-DD)
    - `end` (required): End date (YYYY-MM-DD)
    - `param` (optional): Specific parameter to filter (currently returns all, filter client-side)
    - `limit`: Maximum records to return (default: 1000, max: 10000)
    - `skip`: Pagination offset

    **Rate limit:** 100 requests per minute

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
        api_key: Valid API key

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

    # Get observations
    if station_obj:
        observations = await observation_crud.get_observations_in_date_range(
            db,
            station_id=station_obj.id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
        logger.info(f"Retrieved {len(observations)} observations for {station_obj.name}")
    else:
        # Get all observations in date range (across all stations)
        observations = await observation_crud.get_multi(db, skip=skip, limit=limit)
        # Filter by date range
        observations = [
            obs for obs in observations
            if start_date <= obs.timestamp <= end_date
        ]
        logger.info(f"Retrieved {len(observations)} observations for all stations")

    if param:
        logger.info(f"Note: Parameter filter '{param}' is informational. All parameters returned.")

    return observations


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
    api_key: str = Depends(validate_api_key),
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
