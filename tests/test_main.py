"""
Basic tests for the GMet Weather API.

This module contains unit tests for the main application components.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test the root endpoint returns correct response."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_openapi_docs_available(client):
    """Test that OpenAPI documentation is available."""
    response = client.get("/docs")
    assert response.status_code == 200

    response = client.get("/redoc")
    assert response.status_code == 200

    # OpenAPI JSON is available at /api/v1/openapi.json
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200

    # Verify it's valid JSON with OpenAPI structure
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data


def test_auth_endpoints_structure(client):
    """Test that auth endpoints are properly registered."""
    # Test login endpoint (should require form data, not JSON)
    response = client.post("/api/v1/auth/login")
    assert response.status_code == 422  # Validation error without form data

    # Test register endpoint (should require JSON body)
    response = client.post("/api/v1/auth/register")
    assert response.status_code == 422  # Validation error without body

    # Test protected endpoints (should require auth)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401  # Unauthorized

    response = client.post("/api/v1/auth/apikey/regenerate")
    assert response.status_code == 401  # Unauthorized


def test_weather_endpoints_structure(client):
    """Test that weather endpoints are properly registered."""
    # Test that endpoints exist but require authentication
    response = client.get("/api/v1/weather/stations")
    assert response.status_code == 401  # Unauthorized

    response = client.get("/api/v1/weather/stations/test-station")
    assert response.status_code == 401  # Unauthorized

    response = client.get("/api/v1/weather/observations")
    assert response.status_code == 401  # Unauthorized

    response = client.get("/api/v1/weather/observations/1")
    assert response.status_code == 401  # Unauthorized


def test_cors_middleware_enabled(client):
    """Test that CORS middleware is enabled."""
    response = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    # CORS headers should be present in response
    cors_headers = [h for h in response.headers.keys() if h.startswith("access-control")]
    assert len(cors_headers) > 0


def test_configuration_loaded():
    """Test that configuration is loaded properly."""
    assert settings.API_V1_STR == "/api/v1"
    assert settings.DEBUG is True
    # Check that CORS origins contain expected URLs (as strings for comparison)
    cors_origins_str = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
    assert "http://localhost:3000/" in cors_origins_str
    assert settings.POSTGRES_DB == "gmet_weather.db"


def test_root_response_structure(client):
    """Test that root endpoint returns expected structure."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()

    required_fields = ["message", "version", "docs", "redoc"]
    for field in required_fields:
        assert field in data

    assert "GMet Weather Data API" in data["message"]
    assert data["version"] == "1.0.0"
    assert data["docs"] == "/docs"
    assert data["redoc"] == "/redoc"


def test_status_endpoint_requires_api_key(client):
    """Test that status endpoint requires API key authentication."""
    response = client.get("/api/v1/status")
    assert response.status_code == 401
    assert "API key required" in response.json()["detail"]


def test_status_endpoint_with_registered_user(client):
    """Test status endpoint with API key from registered user."""
    # Register a user to get a valid API key
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "statustest@example.com",
            "password": "testpass123",
            "is_active": True,
            "is_superuser": False
        }
    )
    api_key = register_response.json()["api_key"]

    # Use the API key to access status endpoint
    headers = {"X-API-Key": api_key}
    response = client.get("/api/v1/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["authenticated"] is True
    assert api_key[:8] in data["api_key"]


def test_status_endpoint_with_invalid_api_key(client):
    """Test status endpoint with invalid API key."""
    headers = {"X-API-Key": "invalid-key-12345"}
    response = client.get("/api/v1/status", headers=headers)
    assert response.status_code == 401
