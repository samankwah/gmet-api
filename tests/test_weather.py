"""
Tests for weather endpoints.

This module contains tests for weather data API endpoints including stations and observations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def api_key(client):
    """Create a test user and return API key."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "weathertest@example.com",
            "password": "testpass123",
            "is_active": True,
            "is_superuser": False
        }
    )
    return response.json()["api_key"]


@pytest.fixture
def auth_headers(api_key):
    """Return authentication headers with API key."""
    return {"X-API-Key": api_key}


@pytest.fixture
def test_station(client, auth_headers):
    """Create a test station and return its data."""
    response = client.post(
        "/api/v1/weather/stations",
        json={
            "name": "Test Weather Station",
            "code": "TESTWS001",
            "latitude": 5.6037,
            "longitude": -0.1870,
            "region": "Greater Accra"
        },
        headers=auth_headers
    )
    return response.json()


def test_create_station(client, auth_headers):
    """Test creating a new weather station."""
    response = client.post(
        "/api/v1/weather/stations",
        json={
            "name": "Accra Central Station",
            "code": "ACC001",
            "latitude": 5.6037,
            "longitude": -0.1870,
            "region": "Greater Accra"
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Accra Central Station"
    assert data["code"] == "ACC001"
    assert data["latitude"] == 5.6037
    assert data["longitude"] == -0.1870
    assert data["region"] == "Greater Accra"
    assert "id" in data
    assert "created_at" in data


def test_create_duplicate_station_code(client, auth_headers, test_station):
    """Test that creating a station with duplicate code fails."""
    response = client.post(
        "/api/v1/weather/stations",
        json={
            "name": "Different Station",
            "code": test_station["code"],  # Same code as test_station
            "latitude": 6.0,
            "longitude": -1.0,
            "region": "Ashanti"
        },
        headers=auth_headers
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_get_all_stations(client, auth_headers):
    """Test retrieving all weather stations."""
    # Create multiple stations
    for i in range(3):
        client.post(
            "/api/v1/weather/stations",
            json={
                "name": f"Station {i}",
                "code": f"STN00{i}",
                "latitude": 5.0 + i * 0.1,
                "longitude": -1.0 + i * 0.1,
                "region": "Test Region"
            },
            headers=auth_headers
        )

    response = client.get("/api/v1/weather/stations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


def test_get_stations_by_region(client, auth_headers):
    """Test filtering stations by region."""
    # Create stations in different regions
    client.post(
        "/api/v1/weather/stations",
        json={
            "name": "Ashanti Station 1",
            "code": "ASH001",
            "latitude": 6.0,
            "longitude": -1.0,
            "region": "Ashanti"
        },
        headers=auth_headers
    )

    client.post(
        "/api/v1/weather/stations",
        json={
            "name": "Eastern Station 1",
            "code": "EAST001",
            "latitude": 6.5,
            "longitude": -0.5,
            "region": "Eastern"
        },
        headers=auth_headers
    )

    # Get stations by region
    response = client.get(
        "/api/v1/weather/stations?region=Ashanti",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert all(station["region"] == "Ashanti" for station in data)


def test_get_station_by_code(client, auth_headers, test_station):
    """Test retrieving a specific station by code."""
    response = client.get(
        f"/api/v1/weather/stations/{test_station['code']}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == test_station["code"]
    assert data["name"] == test_station["name"]


def test_get_nonexistent_station(client, auth_headers):
    """Test that getting a non-existent station returns 404."""
    response = client.get(
        "/api/v1/weather/stations/NONEXISTENT",
        headers=auth_headers
    )
    assert response.status_code == 404


def test_create_observation(client, auth_headers, test_station):
    """Test creating a new weather observation."""
    observation_data = {
        "station_id": test_station["id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 28.5,
        "humidity": 75.0,
        "wind_speed": 12.5,
        "wind_direction": 180.0,
        "rainfall": 2.5,
        "pressure": 1013.25
    }

    response = client.post(
        "/api/v1/weather/observations",
        json=observation_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["station_id"] == test_station["id"]
    assert data["temperature"] == 28.5
    assert data["humidity"] == 75.0
    assert "id" in data


def test_create_observation_invalid_station(client, auth_headers):
    """Test that creating observation with invalid station fails."""
    observation_data = {
        "station_id": 99999,  # Non-existent station
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": 28.5,
        "humidity": 75.0,
        "wind_speed": 12.5,
        "wind_direction": 180.0,
        "rainfall": 0.0,
        "pressure": 1013.25
    }

    response = client.post(
        "/api/v1/weather/observations",
        json=observation_data,
        headers=auth_headers
    )
    assert response.status_code == 400


def test_get_all_observations(client, auth_headers, test_station):
    """Test retrieving all observations."""
    # Create multiple observations
    for i in range(3):
        client.post(
            "/api/v1/weather/observations",
            json={
                "station_id": test_station["id"],
                "timestamp": (datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
                "temperature": 25.0 + i,
                "humidity": 70.0,
                "wind_speed": 10.0,
                "wind_direction": 180.0,
                "rainfall": 0.0,
                "pressure": 1013.0
            },
            headers=auth_headers
        )

    response = client.get("/api/v1/weather/observations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


def test_get_observation_by_id(client, auth_headers, test_station):
    """Test retrieving a specific observation by ID."""
    # Create observation
    create_response = client.post(
        "/api/v1/weather/observations",
        json={
            "station_id": test_station["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature": 28.0,
            "humidity": 70.0,
            "wind_speed": 10.0,
            "wind_direction": 180.0,
            "rainfall": 0.0,
            "pressure": 1013.0
        },
        headers=auth_headers
    )
    observation_id = create_response.json()["id"]

    # Get observation by ID
    response = client.get(
        f"/api/v1/weather/observations/{observation_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == observation_id
    assert data["temperature"] == 28.0


def test_get_latest_observation_for_station(client, auth_headers, test_station):
    """Test retrieving the latest observation for a station."""
    # Create multiple observations
    for i in range(3):
        client.post(
            "/api/v1/weather/observations",
            json={
                "station_id": test_station["id"],
                "timestamp": (datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
                "temperature": 25.0 + i,
                "humidity": 70.0,
                "wind_speed": 10.0,
                "wind_direction": 180.0,
                "rainfall": 0.0,
                "pressure": 1013.0
            },
            headers=auth_headers
        )

    # Get latest observation
    response = client.get(
        f"/api/v1/weather/stations/{test_station['code']}/latest",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["temperature"] == 27.0  # Latest observation has temp 25.0 + 2


def test_get_observations_by_station(client, auth_headers):
    """Test filtering observations by station."""
    # Create two stations
    station1 = client.post(
        "/api/v1/weather/stations",
        json={
            "name": "Filter Station 1",
            "code": "FLT001",
            "latitude": 5.0,
            "longitude": -1.0,
            "region": "Test"
        },
        headers=auth_headers
    ).json()

    station2 = client.post(
        "/api/v1/weather/stations",
        json={
            "name": "Filter Station 2",
            "code": "FLT002",
            "latitude": 6.0,
            "longitude": -2.0,
            "region": "Test"
        },
        headers=auth_headers
    ).json()

    # Create observations for each station
    client.post(
        "/api/v1/weather/observations",
        json={
            "station_id": station1["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature": 25.0,
            "humidity": 70.0,
            "wind_speed": 10.0,
            "wind_direction": 180.0,
            "rainfall": 0.0,
            "pressure": 1013.0
        },
        headers=auth_headers
    )

    client.post(
        "/api/v1/weather/observations",
        json={
            "station_id": station2["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature": 30.0,
            "humidity": 75.0,
            "wind_speed": 15.0,
            "wind_direction": 90.0,
            "rainfall": 5.0,
            "pressure": 1010.0
        },
        headers=auth_headers
    )

    # Get observations for station1 only
    response = client.get(
        f"/api/v1/weather/observations?station_id={station1['id']}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    # All observations should be from station1
    for obs in data:
        if obs["station_id"] == station1["id"]:
            assert obs["temperature"] == 25.0


def test_weather_endpoints_require_authentication(client):
    """Test that weather endpoints require authentication."""
    # Stations endpoint
    response = client.get("/api/v1/weather/stations")
    assert response.status_code == 401

    # Create station endpoint
    response = client.post(
        "/api/v1/weather/stations",
        json={
            "name": "Test",
            "code": "TEST",
            "latitude": 0.0,
            "longitude": 0.0,
            "region": "Test"
        }
    )
    assert response.status_code == 401

    # Observations endpoint
    response = client.get("/api/v1/weather/observations")
    assert response.status_code == 401


def test_pagination_works(client, auth_headers, test_station):
    """Test that pagination works for observations."""
    # Create 10 observations
    for i in range(10):
        client.post(
            "/api/v1/weather/observations",
            json={
                "station_id": test_station["id"],
                "timestamp": (datetime.now(timezone.utc) + timedelta(minutes=i)).isoformat(),
                "temperature": 25.0,
                "humidity": 70.0,
                "wind_speed": 10.0,
                "wind_direction": 180.0,
                "rainfall": 0.0,
                "pressure": 1013.0
            },
            headers=auth_headers
        )

    # Get first 5
    response = client.get(
        "/api/v1/weather/observations?skip=0&limit=5",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5

    # Get next 5
    response = client.get(
        "/api/v1/weather/observations?skip=5&limit=5",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
