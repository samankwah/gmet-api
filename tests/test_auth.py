"""
Tests for authentication endpoints.

This module contains tests for user registration, login, and API key management.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.crud.user import user as user_crud
from app.schemas.auth import UserCreate


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

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


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
async def test_user(db):
    """Create a test user."""
    user_in = UserCreate(
        email="test@example.com",
        password="testpassword123",
        is_active=True,
        is_superuser=False
    )
    user = await user_crud.create(db, obj_in=user_in)
    return user


def test_register_new_user(client):
    """Test user registration with valid data."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "is_active": True,
            "is_superuser": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
    assert data["email"] == "newuser@example.com"
    assert data["is_active"] is True
    assert "user_id" in data


def test_register_duplicate_email(client):
    """Test that registering with duplicate email fails."""
    # Register first user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "password123",
            "is_active": True,
            "is_superuser": False
        }
    )

    # Try to register with same email
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "differentpass456",
            "is_active": True,
            "is_superuser": False
        }
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_register_invalid_email(client):
    """Test registration with invalid email format."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "notanemail",
            "password": "password123",
            "is_active": True,
            "is_superuser": False
        }
    )
    assert response.status_code == 422  # Validation error


def test_login_success(client):
    """Test successful login with valid credentials."""
    # First register a user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "logintest@example.com",
            "password": "testpass123",
            "is_active": True,
            "is_superuser": False
        }
    )

    # Now try to login
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "logintest@example.com",  # OAuth2 uses 'username' field
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "logintest@example.com"
    assert "expires_in" in data


def test_login_wrong_password(client):
    """Test login with incorrect password."""
    # Register a user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "correctpass",
            "is_active": True,
            "is_superuser": False
        }
    )

    # Try to login with wrong password
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "wrongpass@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user(client):
    """Test login with non-existent email."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "doesnotexist@example.com",
            "password": "anypassword"
        }
    )
    assert response.status_code == 401


def test_get_current_user_info(client):
    """Test getting current user information."""
    # Register and get API key
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "userinfo@example.com",
            "password": "password123",
            "is_active": True,
            "is_superuser": False
        }
    )
    api_key = register_response.json()["api_key"]

    # Get user info with API key
    response = client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": api_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "userinfo@example.com"
    assert data["api_key"] == api_key
    assert data["is_active"] is True


def test_get_current_user_without_auth(client):
    """Test that /me endpoint requires authentication."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_regenerate_api_key(client):
    """Test API key regeneration."""
    # Register user
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "regenkey@example.com",
            "password": "password123",
            "is_active": True,
            "is_superuser": False
        }
    )
    old_api_key = register_response.json()["api_key"]

    # Regenerate API key
    response = client.post(
        "/api/v1/auth/apikey/regenerate",
        headers={"X-API-Key": old_api_key}
    )
    assert response.status_code == 200
    data = response.json()
    new_api_key = data["api_key"]

    # Verify new key is different
    assert new_api_key != old_api_key

    # Verify old key no longer works
    old_key_response = client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": old_api_key}
    )
    assert old_key_response.status_code == 401

    # Verify new key works
    new_key_response = client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": new_api_key}
    )
    assert new_key_response.status_code == 200


def test_inactive_user_cannot_login(client):
    """Test that inactive users cannot login."""
    # Register inactive user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "inactive@example.com",
            "password": "password123",
            "is_active": False,
            "is_superuser": False
        }
    )

    # Try to login
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "inactive@example.com",
            "password": "password123"
        }
    )
    # Should fail with 403 (Forbidden) due to inactive account
    assert response.status_code in [401, 403]
