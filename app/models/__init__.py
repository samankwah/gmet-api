# Database models package

from app.models.base import BaseModel
from app.models.user import User
from app.models.api_key import APIKey
from app.models.station import Station
from app.models.synoptic_observation import SynopticObservation
from app.models.daily_summary import DailySummary

# Phase 1 Climate Products
from app.models.weekly_summary import WeeklySummary
from app.models.monthly_summary import MonthlySummary

# Phase 2 Climate Products
from app.models.dekadal_summary import DekadalSummary
from app.models.seasonal_summary import SeasonalSummary
from app.models.annual_summary import AnnualSummary
from app.models.climate_normal import ClimateNormal

# Backward compatibility: keep Observation as alias for SynopticObservation
# This allows existing code to continue working during migration
from app.models.synoptic_observation import SynopticObservation as Observation

__all__ = [
    "BaseModel",
    "User",
    "APIKey",
    "Station",
    "SynopticObservation",
    "DailySummary",
    "WeeklySummary",
    "MonthlySummary",
    "DekadalSummary",
    "SeasonalSummary",
    "AnnualSummary",
    "ClimateNormal",
    "Observation",  # Backward compatibility alias
]

# Configure all mappers after all models are imported
# This resolves bidirectional relationships defined with string references
from sqlalchemy.orm import configure_mappers
configure_mappers()
