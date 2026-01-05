"""
Weather data database models (DEPRECATED).

This module is maintained for backward compatibility.
New code should import directly from:
- app.models.station import Station
- app.models.synoptic_observation import SynopticObservation
- app.models.daily_summary import DailySummary

The Observation class is an alias for SynopticObservation.
"""

# Import new models
from app.models.station import Station
from app.models.synoptic_observation import SynopticObservation
from app.models.daily_summary import DailySummary

# Backward compatibility: Observation is an alias for SynopticObservation
Observation = SynopticObservation

# Export for backward compatibility
__all__ = ["Station", "Observation", "SynopticObservation", "DailySummary"]
