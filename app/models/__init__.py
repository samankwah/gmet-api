# Database models package

from app.models.base import BaseModel
from app.models.user import User
from app.models.api_key import APIKey
from app.models.station import Station
from app.models.synoptic_observation import SynopticObservation
from app.models.daily_summary import DailySummary

# Backward compatibility: keep Observation as alias for SynopticObservation
# This allows existing code to continue working during migration
from app.models.synoptic_observation import SynopticObservation as Observation

# NOTE: Phase 1/2 Climate Products (WeeklySummary, MonthlySummary, DekadalSummary,
# SeasonalSummary, AnnualSummary, ClimateNormal) are not imported here to avoid
# SQLAlchemy mapper configuration errors. They can be re-added when those features
# are implemented and the Station model relationships are restored.

__all__ = [
    "BaseModel",
    "User",
    "APIKey",
    "Station",
    "SynopticObservation",
    "DailySummary",
    "Observation",  # Backward compatibility alias
]
