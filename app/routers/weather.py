"""
Weather data router.

This module contains endpoints for weather data including current conditions,
forecasts, and historical data.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request, status, Body, Security
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.dependencies.auth import get_api_key
from app.models.api_key import APIKey
from app.schemas.weather import (
    StationResponse,
    ObservationResponse,
    StationCreate,
    ObservationCreate,
    WeatherQueryParams
)
from app.crud.weather import station as station_crud, observation as observation_crud

router = APIRouter(
    prefix="/weather",
    tags=["Weather Data Management"],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Not found"}
    },
)

limiter = Limiter(key_func=get_remote_address)


@router.get("/stations", response_model=List[StationResponse])
@limiter.limit("100/minute")
async def get_weather_stations(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    region: Optional[str] = Query(None, description="Filter by region"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of weather stations.

    Supports filtering by region and pagination.

    Rate limit: 100 requests per minute

    **Note:** This endpoint is publicly accessible (no authentication required).
    """
    if region:
        stations = await station_crud.get_by_region(
            db, region=region, skip=skip, limit=limit
        )
    else:
        stations = await station_crud.get_multi(db, skip=skip, limit=limit)

    return stations


@router.get("/stations/{station_code}", response_model=StationResponse)
@limiter.limit("100/minute")
async def get_station_details(
    request: Request,
    station_code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a specific weather station.

    Rate limit: 100 requests per minute

    **Note:** This endpoint is publicly accessible (no authentication required).
    """
    station = await station_crud.get_by_code(db, code=station_code)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station with code '{station_code}' not found"
        )
    return station


@router.get("/observations", response_model=List[ObservationResponse])
@limiter.limit("100/minute")
async def get_observations(
    request: Request,
    station_id: Optional[int] = Query(None, description="Filter by station ID"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    hours: Optional[int] = Query(None, ge=1, le=168, description="Get observations from last N hours"),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Get weather observations.

    Supports filtering by station, date range, or recent hours.

    Rate limit: 100 requests per minute
    """
    if station_id and start_date and end_date:
        # Get observations for a specific station within date range
        observations = await observation_crud.get_observations_in_date_range(
            db,
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
    elif hours:
        # Get recent observations from all stations
        observations = await observation_crud.get_recent_observations(
            db, hours=hours, skip=skip, limit=limit
        )
    else:
        # Get all observations with pagination
        observations = await observation_crud.get_multi(db, skip=skip, limit=limit)

    return observations


@router.get("/observations/{observation_id}", response_model=ObservationResponse)
@limiter.limit("100/minute")
async def get_observation(
    request: Request,
    observation_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Get a specific weather observation by ID.

    Rate limit: 100 requests per minute
    """
    observation = await observation_crud.get(db, id=observation_id)
    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observation with id {observation_id} not found"
        )
    return observation


@router.get("/stations/{station_code}/latest", response_model=ObservationResponse)
@limiter.limit("100/minute")
async def get_latest_observation(
    request: Request,
    station_code: str,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Get the latest observation for a specific weather station.

    Rate limit: 100 requests per minute
    """
    # First get the station by code
    station = await station_crud.get_by_code(db, code=station_code)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station with code '{station_code}' not found"
        )

    # Get the latest observation for this station
    observation = await observation_crud.get_latest_for_station(db, station_id=station.id)
    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No observations found for station '{station_code}'"
        )

    return observation


@router.post("/stations", response_model=StationResponse)
@limiter.limit("10/minute")  # Lower limit for write operations
async def create_station(
    request: Request,
    station: StationCreate,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Create a new weather station.

    Rate limit: 10 requests per minute (write operation)
    """
    # Check if station code already exists
    existing_station = await station_crud.get_by_code(db, code=station.code)
    if existing_station:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Station with code '{station.code}' already exists"
        )

    return await station_crud.create(db, obj_in=station)


@router.post("/observations", response_model=ObservationResponse)
@limiter.limit("60/minute")  # Higher limit for observations (sensors posting data)
async def create_observation(
    request: Request,
    observation: ObservationCreate,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Security(get_api_key),
):
    """
    Create a new weather observation.

    Rate limit: 60 requests per minute (write operation for sensors)
    """
    # Verify that the station exists
    station = await station_crud.get(db, id=observation.station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Station with id {observation.station_id} does not exist"
        )

    return await observation_crud.create(db, obj_in=observation)
