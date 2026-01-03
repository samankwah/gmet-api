"""
Main FastAPI application for GMet Weather Data API.

This module contains the main FastAPI application instance and root endpoint.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.status import router as status_router
from app.routers.weather import router as weather_router
from app.routers.pdr_v1 import router as pdr_v1_router
from app.utils.logging_config import setup_logging, get_logger

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
