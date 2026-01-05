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

__all__ = [
    "BaseModel",
    "User",
    "APIKey",
    "Station",
    "SynopticObservation",
    "DailySummary",
    "Observation",  # Backward compatibility alias
]
