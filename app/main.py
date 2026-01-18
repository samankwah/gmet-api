"""
Main FastAPI application for GMet Weather Data API.

This module contains the main FastAPI application instance and root endpoint.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.status import router as status_router
from app.routers.weather import router as weather_router
from app.routers.pdr_v1 import router as pdr_v1_router
from app.routers.products import router as products_router
from app.routers.agro import router as agro_router
from app.api.v1.endpoints.api_keys import router as api_keys_router
from app.utils.logging_config import setup_logging, get_logger

# Import all models to ensure SQLAlchemy relationships are properly configured
import app.models  # noqa: F401 - triggers import of all model classes

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown events.

    Note: Database tables are managed through Alembic migrations.
    Run `alembic upgrade head` to create/update database tables.
    """
    # Startup
    logger.info("=" * 60)
    logger.info("GMet Weather API - Application starting up")
    logger.info(f"Environment: {'Development' if settings.DEBUG else 'Production'}")
    logger.info(f"API Version: {settings.API_V1_STR}")
    logger.info(f"Database: {settings.SQLALCHEMY_DATABASE_URI.split('://')[0]}")
    logger.info("=" * 60)
    logger.warning("Remember to run 'alembic upgrade head' to apply database migrations")

    # Configure SQLAlchemy mappers to resolve all relationships
    # This must happen after all models are imported (via app.models import in this file)
    from sqlalchemy.orm import configure_mappers
    configure_mappers()
    logger.info("SQLAlchemy mappers configured successfully")

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("GMet Weather API - Application shutting down")
    logger.info("=" * 60)
    # Add cleanup logic here if needed


app = FastAPI(
    title="GMet Weather Data API",
    description="RESTful API for Ghana Meteorological Agency weather data",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Add exception handler for 401 Unauthorized - FIXED VERSION
@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    """Handle 401 Unauthorized exceptions."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "detail": exc.detail,
            "status_code": status.HTTP_401_UNAUTHORIZED
        },
        headers=exc.headers or {}
    )

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW}seconds")
async def root(request: Request):
    """
    Root endpoint returning API information.

    Rate limit: {settings.RATE_LIMIT_REQUESTS} requests per {settings.RATE_LIMIT_WINDOW} seconds
    """
    return {
        "message": "Welcome to GMet Weather Data API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
@limiter.limit("60/minute")  # More generous limit for health checks
async def health_check(request: Request):
    """
    Health check endpoint.

    Rate limit: 60 requests per minute
    """
    return {"status": "healthy"}


# Include routers
# PDR v1 compliant endpoints (as per Project Design Document)
app.include_router(pdr_v1_router)

# Standard API v1 endpoints
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(status_router, prefix=settings.API_V1_STR)
app.include_router(weather_router, prefix=settings.API_V1_STR)
app.include_router(products_router, prefix=settings.API_V1_STR)
app.include_router(agro_router, prefix=settings.API_V1_STR)
app.include_router(api_keys_router, prefix=settings.API_V1_STR)


# Customize OpenAPI schema to properly show API Key authentication
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    # Extended API description with features and authentication
    description = """
## Ghana Meteorological Agency Weather Data API

RESTful API providing comprehensive weather and climate data for Ghana.

### 🌍 Quick Start Guide

**For External Applications (Public Use):**
- Use **Public Weather API (v1)** endpoints (`/v1/*`)
- Get current weather, daily summaries, and historical data
- User-friendly location input (city names accepted)

**For Internal Systems & Data Ingestion:**
- Use **Weather Data Management** endpoints (`/api/v1/weather/*`)
- Manage stations and ingest observation data
- Technical CRUD operations

**For Climate Analysis:**
- Use **Climate Products** endpoints (`/api/v1/products/*`)
- WMO-compliant aggregations (daily, weekly, monthly, seasonal, annual)

**For Agricultural Applications:**
- Use **Agrometeorological Products** endpoints (`/api/v1/agro/*`)
- Growing Degree Days, water balance, planting advisories

---

### 📚 Features

- **Real-time Weather Observations**: Current weather data from synoptic stations across Ghana
- **Historical Climate Data**: Long-term weather records for climate analysis and research
- **Climate Products**: WMO-compliant aggregations
  - Daily weather summaries with min/max temperatures
  - Weekly summaries (ISO 8601 standard)
  - Monthly summaries with climate anomalies (compared to 1991-2020 normals)
  - Dekadal summaries (10-day periods for agricultural monitoring)
  - Seasonal summaries (MAM, JJA, SON, DJF)
  - Annual summaries with extremes
- **Agrometeorological Products**: Agricultural decision support
  - Growing Degree Days (GDD) for crops (maize, rice, sorghum)
  - Reference Evapotranspiration (ET₀) using Hargreaves method
  - Crop water balance for irrigation planning
  - Rainy season onset/cessation detection (WMO criteria)

---

### 🔐 Authentication

**Public endpoints (no API key required):**
- `GET /v1/current` - Get current weather for any location
- `GET /v1/historical` - Get historical weather data
- `GET /v1/daily-summaries/{station_code}` - Get daily weather summaries

**Protected endpoints (API key required):**
- Admin endpoints, data modification, and internal APIs require an API key via the `X-API-Key` header

**To authenticate for protected endpoints:**
1. Obtain an API key from your GMet administrator
2. Click the **"Authorize"** button above (🔓 icon)
3. Enter your API key in the `X-API-Key` field
4. Click "Authorize"
5. Try out any endpoint using the "Try it out" button

---

### 📊 Data Standards

- **WMO Compliance**: All climate products follow World Meteorological Organization guidelines
- **Quality Assurance**: Data completeness thresholds ensure reliable aggregations (70-80% minimum)
- **Scientific Accuracy**: Agrometeorological products use peer-reviewed methods:
  - FAO-56 for evapotranspiration
  - WMO Guide to Agricultural Meteorological Practices (GAMP)
  - Ghana-calibrated crop parameters

---

### 🚀 Quick Examples

**Get current weather in Accra:**
```
GET /v1/current?location=Accra
```

**Get monthly summary with climate anomaly:**
```
GET /api/v1/products/monthly?station_code=DGAA&year=2024&month=5
```

**Calculate Growing Degree Days for maize:**
```
GET /api/v1/agro/gdd?station_code=04003NAV&start_date=2024-03-15&end_date=2024-06-30&crop=maize
```

**Detect rainy season onset:**
```
GET /api/v1/agro/onset-cessation?station_code=04003NAV&year=2024&season=MAM
```
    """

    openapi_schema = get_openapi(
        title="GMet Weather Data API",
        version="1.0.0",
        description=description,
        routes=app.routes,
    )

    # Add contact information
    openapi_schema["info"]["contact"] = {
        "name": "GMet API Support",
        "email": "api@gmet.gov.gh",
        "url": "https://gmet.gov.gh"
    }

    # Add license information
    openapi_schema["info"]["license"] = {
        "name": "Proprietary",
        "url": "https://gmet.gov.gh/terms"
    }

    # Properly define security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication. Obtain from your administrator."
        },
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for user authentication (optional)"
        }
    }

    # Organize endpoint tags in logical order
    openapi_schema["tags"] = [
        {
            "name": "Public Weather API (v1)",
            "description": """**Official public-facing weather API** - Use these endpoints for external applications.

**🔓 No API key required for these endpoints!**

**Features:**
- User-friendly location input (city names or station codes)
- Daily weather summaries (min/max temperatures)
- Current weather conditions
- Historical weather data

**URL Pattern:** `/v1/*`

**Best for:** Mobile apps, dashboards, public integrations, external applications

**Example:** `/v1/current?location=Accra` - Get current weather in Accra (no API key needed!)"""
        },
        {
            "name": "Weather Data Management",
            "description": """**Internal API for weather data management** - Technical endpoints for data ingestion and station administration.

**Features:**
- Create and manage weather stations
- Ingest observation data from sensors
- Raw synoptic observations (instantaneous readings)
- CRUD operations for stations and observations

**URL Pattern:** `/api/v1/weather/*`

**Best for:** Data ingestion pipelines, sensor integration, internal GMet systems, admin tools

**Note:** Some endpoints do not require authentication for public station information."""
        },
        {
            "name": "Climate Products",
            "description": """**WMO-compliant climate aggregations** - Processed climate data following World Meteorological Organization standards.

**Products:**
- Daily weather summaries
- Weekly summaries (ISO 8601)
- Monthly summaries with climate anomalies
- Dekadal summaries (10-day periods)
- Seasonal summaries (MAM, JJA, SON, DJF)
- Annual summaries

**URL Pattern:** `/api/v1/products/*`

**Best for:** Climate analysis, long-term trends, research, climate monitoring"""
        },
        {
            "name": "Agrometeorological Products",
            "description": """**Agricultural decision support products** - Specialized meteorological data for farming and agriculture.

**Products:**
- Growing Degree Days (GDD) for crops (maize, rice, sorghum)
- Reference Evapotranspiration (ET₀) using Hargreaves method
- Crop water balance for irrigation planning
- Rainy season onset/cessation detection (WMO criteria)

**URL Pattern:** `/api/v1/agro/*`

**Best for:** Farming applications, irrigation planning, planting advisories, agricultural extension services"""
        },
        {
            "name": "status",
            "description": "Health check and system status endpoints - No authentication required"
        },
        {
            "name": "authentication",
            "description": "User authentication and session management"
        },
        {
            "name": "API Keys",
            "description": "API key management - Admin only"
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi