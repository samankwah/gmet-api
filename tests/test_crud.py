"""
Tests for CRUD operations.

This module contains tests for database CRUD operations for users, stations, and observations.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.crud.user import user as user_crud
from app.crud.weather import station as station_crud, observation as observation_crud
from app.schemas.auth import UserCreate, UserUpdate
from app.schemas.weather import StationCreate, ObservationCreate


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_crud.db"

# Create async engine for testing
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture
async def db():
    """Create test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# User CRUD Tests
@pytest.mark.asyncio
async def test_create_user(db):
    """Test creating a new user."""
    user_in = UserCreate(
        email="crud_test@example.com",
        password="testpassword",
        is_active=True,
        is_superuser=False
    )
    user = await user_crud.create(db, obj_in=user_in)

    assert user.email == "crud_test@example.com"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.api_key is not None
    assert len(user.api_key) == 32
    assert user.id is not None


@pytest.mark.asyncio
async def test_get_user_by_email(db):
    """Test retrieving user by email."""
    user_in = UserCreate(
        email="getbyemail@example.com",
        password="password",
        is_active=True,
        is_superuser=False
    )
    created_user = await user_crud.create(db, obj_in=user_in)

    retrieved_user = await user_crud.get_by_email(db, email="getbyemail@example.com")

    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.email == "getbyemail@example.com"


@pytest.mark.asyncio
async def test_get_user_by_api_key(db):
    """Test retrieving user by API key."""
    user_in = UserCreate(
        email="getbykey@example.com",
        password="password",
        is_active=True,
        is_superuser=False
    )
    created_user = await user_crud.create(db, obj_in=user_in)

    retrieved_user = await user_crud.get_by_api_key(db, api_key=created_user.api_key)

    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.api_key == created_user.api_key


@pytest.mark.asyncio
async def test_update_user(db):
    """Test updating user information."""
    user_in = UserCreate(
        email="updatetest@example.com",
        password="oldpassword",
        is_active=True,
        is_superuser=False
    )
    user = await user_crud.create(db, obj_in=user_in)

    update_data = UserUpdate(
        email="updatetest@example.com",
        is_active=False,
        is_superuser=True
    )
    updated_user = await user_crud.update(db, db_obj=user, obj_in=update_data)

    assert updated_user.is_active is False
    assert updated_user.is_superuser is True
    assert updated_user.email == "updatetest@example.com"


# Station CRUD Tests
@pytest.mark.asyncio
async def test_create_station(db):
    """Test creating a new weather station."""
    station_in = StationCreate(
        name="Test Station",
        code="TEST001",
        latitude=5.6037,
        longitude=-0.1870,
        region="Greater Accra"
    )
    station = await station_crud.create(db, obj_in=station_in)

    assert station.name == "Test Station"
    assert station.code == "TEST001"
    assert station.latitude == 5.6037
    assert station.longitude == -0.1870
    assert station.region == "Greater Accra"
    assert station.id is not None


@pytest.mark.asyncio
async def test_get_station_by_code(db):
    """Test retrieving station by code."""
    station_in = StationCreate(
        name="Code Test Station",
        code="CODE001",
        latitude=5.6037,
        longitude=-0.1870,
        region="Greater Accra"
    )
    created_station = await station_crud.create(db, obj_in=station_in)

    retrieved_station = await station_crud.get_by_code(db, code="CODE001")

    assert retrieved_station is not None
    assert retrieved_station.id == created_station.id
    assert retrieved_station.code == "CODE001"


@pytest.mark.asyncio
async def test_get_stations_by_region(db):
    """Test retrieving stations by region."""
    # Create multiple stations in same region
    for i in range(3):
        station_in = StationCreate(
            name=f"Ashanti Station {i}",
            code=f"ASH00{i}",
            latitude=6.0 + i * 0.1,
            longitude=-1.0 + i * 0.1,
            region="Ashanti"
        )
        await station_crud.create(db, obj_in=station_in)

    # Create station in different region
    other_station = StationCreate(
        name="Eastern Station",
        code="EAST001",
        latitude=6.5,
        longitude=-0.5,
        region="Eastern"
    )
    await station_crud.create(db, obj_in=other_station)

    # Get stations by region
    ashanti_stations = await station_crud.get_by_region(db, region="Ashanti")

    assert len(ashanti_stations) == 3
    for station in ashanti_stations:
        assert station.region == "Ashanti"


# Observation CRUD Tests
@pytest.mark.asyncio
async def test_create_observation(db):
    """Test creating a new observation."""
    # First create a station
    station_in = StationCreate(
        name="Observation Test Station",
        code="OBS001",
        latitude=5.6037,
        longitude=-0.1870,
        region="Greater Accra"
    )
    station = await station_crud.create(db, obj_in=station_in)

    # Create observation
    observation_in = ObservationCreate(
        station_id=station.id,
        timestamp=datetime.now(timezone.utc),
        temperature=28.5,
        humidity=75.0,
        wind_speed=12.5,
        wind_direction=180.0,
        rainfall=0.0,
        pressure=1013.25
    )
    observation = await observation_crud.create(db, obj_in=observation_in)

    assert observation.station_id == station.id
    assert observation.temperature == 28.5
    assert observation.humidity == 75.0
    assert observation.wind_speed == 12.5
    assert observation.id is not None


@pytest.mark.asyncio
async def test_get_latest_observation_for_station(db):
    """Test retrieving the latest observation for a station."""
    # Create station
    station_in = StationCreate(
        name="Latest Test Station",
        code="LATEST001",
        latitude=5.6037,
        longitude=-0.1870,
        region="Greater Accra"
    )
    station = await station_crud.create(db, obj_in=station_in)

    # Create multiple observations
    from datetime import timedelta
    base_time = datetime.now(timezone.utc)

    for i in range(3):
        observation_in = ObservationCreate(
            station_id=station.id,
            timestamp=base_time + timedelta(hours=i),
            temperature=25.0 + i,
            humidity=70.0,
            wind_speed=10.0,
            wind_direction=180.0,
            rainfall=0.0,
            pressure=1013.0
        )
        await observation_crud.create(db, obj_in=observation_in)

    # Get latest observation
    latest = await observation_crud.get_latest_for_station(db, station_id=station.id)

    assert latest is not None
    assert latest.temperature == 27.0  # Last observation has temp 25.0 + 2
    assert latest.station_id == station.id


@pytest.mark.asyncio
async def test_get_observations_in_date_range(db):
    """Test retrieving observations within a date range."""
    # Create station
    station_in = StationCreate(
        name="Range Test Station",
        code="RANGE001",
        latitude=5.6037,
        longitude=-0.1870,
        region="Greater Accra"
    )
    station = await station_crud.create(db, obj_in=station_in)

    # Create observations over 5 days
    from datetime import timedelta
    base_time = datetime.now(timezone.utc)

    for i in range(5):
        observation_in = ObservationCreate(
            station_id=station.id,
            timestamp=base_time + timedelta(days=i),
            temperature=25.0,
            humidity=70.0,
            wind_speed=10.0,
            wind_direction=180.0,
            rainfall=0.0,
            pressure=1013.0
        )
        await observation_crud.create(db, obj_in=observation_in)

    # Get observations in middle 3 days
    start_date = base_time + timedelta(days=1)
    end_date = base_time + timedelta(days=3)

    observations = await observation_crud.get_observations_in_date_range(
        db,
        station_id=station.id,
        start_date=start_date,
        end_date=end_date
    )

    assert len(observations) >= 2  # Should get days 1, 2, and possibly 3


@pytest.mark.asyncio
async def test_delete_station_cascade_deletes_observations(db):
    """Test that deleting a station also deletes its observations (cascade)."""
    # Create station
    station_in = StationCreate(
        name="Cascade Test Station",
        code="CASCADE001",
        latitude=5.6037,
        longitude=-0.1870,
        region="Greater Accra"
    )
    station = await station_crud.create(db, obj_in=station_in)

    # Create observation
    observation_in = ObservationCreate(
        station_id=station.id,
        timestamp=datetime.now(timezone.utc),
        temperature=28.0,
        humidity=70.0,
        wind_speed=10.0,
        wind_direction=180.0,
        rainfall=0.0,
        pressure=1013.0
    )
    observation = await observation_crud.create(db, obj_in=observation_in)

    # Delete station
    await station_crud.remove(db, id=station.id)

    # Verify observation is also deleted
    retrieved_observation = await observation_crud.get(db, id=observation.id)
    assert retrieved_observation is None
