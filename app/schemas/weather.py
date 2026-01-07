"""
Weather data schemas.

This module contains Pydantic schemas for weather data requests and responses.
"""

from datetime import datetime, timezone
from datetime import date as DateType
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.base import BaseSchema, TimestampSchema, IDSchema


class StationBase(BaseSchema):
    """Base weather station schema."""
    name: str
    code: str = Field(..., description="Unique station code")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    region: str = Field(..., description="Region or city name")


class StationCreate(StationBase):
    """Schema for creating a weather station."""
    pass


class StationUpdate(BaseSchema):
    """Schema for updating weather station information."""
    name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    region: Optional[str] = None


class Station(StationBase, IDSchema, TimestampSchema):
    """Complete weather station schema."""
    pass


class ObservationBase(BaseSchema):
    """
    Base weather observation schema with data validation.

    All weather parameters are validated against realistic ranges for Ghana's climate.
    """
    station_id: int
    obs_datetime: datetime

    # Weather measurements with realistic ranges for Ghana
    temperature: Optional[float] = Field(
        None,
        description="Temperature in Celsius (realistic range: 15-45°C)"
    )
    relative_humidity: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Relative humidity percentage (0-100%)"
    )
    wind_speed: Optional[float] = Field(
        None,
        ge=0,
        description="Wind speed in m/s (realistic range: 0-50 m/s)"
    )
    wind_direction: Optional[float] = Field(
        None,
        ge=0,
        le=360,
        description="Wind direction in degrees (0-360°, 0=North)"
    )
    rainfall: Optional[float] = Field(
        None,
        ge=0,
        description="Rainfall in mm (realistic max: 500mm per observation)"
    )
    pressure: Optional[float] = Field(
        None,
        description="Atmospheric pressure in hPa (realistic range: 950-1050 hPa)"
    )

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        """
        Validate temperature is within realistic range for Ghana.

        Ghana's climate: Typical range 15°C to 45°C
        """
        if v is not None:
            if v < -10 or v > 60:
                raise ValueError(
                    f'Temperature {v}°C is out of realistic range (-10°C to 60°C). '
                    'Please verify the reading.'
                )
            if v < 15 or v > 45:
                # Warning range but still allow (for exceptional conditions)
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f'Temperature {v}°C is unusual for Ghana (typical: 15-45°C). '
                    'Please verify this is correct.'
                )
        return v

    @field_validator('wind_speed')
    @classmethod
    def validate_wind_speed(cls, v):
        """Validate wind speed is reasonable."""
        if v is not None and v > 50:
            raise ValueError(
                f'Wind speed {v} m/s is exceptionally high. '
                'Maximum realistic value is 50 m/s (~180 km/h). Please verify.'
            )
        return v

    @field_validator('rainfall')
    @classmethod
    def validate_rainfall(cls, v):
        """
        Validate rainfall amount is reasonable.

        Ghana can experience heavy rainfall, but >500mm in one observation
        period is extremely rare and likely an error.
        """
        if v is not None:
            if v > 500:
                raise ValueError(
                    f'Rainfall {v} mm is exceptionally high. '
                    'Please verify this measurement (typical max: 500mm per observation).'
                )
            if v > 200:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f'Rainfall {v} mm is very high. Please verify this is correct.'
                )
        return v

    @field_validator('pressure')
    @classmethod
    def validate_pressure(cls, v):
        """
        Validate atmospheric pressure is within realistic range.

        Sea level pressure typically ranges from 980-1040 hPa.
        """
        if v is not None:
            if v < 950 or v > 1050:
                raise ValueError(
                    f'Pressure {v} hPa is out of realistic range (950-1050 hPa). '
                    'Please verify this measurement.'
                )
        return v

    @field_validator('obs_datetime')
    @classmethod
    def validate_obs_datetime(cls, v):
        """
        Validate obs_datetime is not in the future.

        Weather observations should be for current or past times only.
        """
        if v is not None:
            now = datetime.now(timezone.utc)
            # Make obs_datetime timezone-aware if it isn't
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)

            if v > now:
                raise ValueError(
                    f'Observation datetime {v} is in the future. '
                    'Observations must be for current or past times.'
                )
        return v

    @model_validator(mode='after')
    def validate_observation_completeness(self):
        """
        Validate that the observation has at least some weather data.

        An observation should have at least one weather parameter.
        """
        weather_params = [
            self.temperature,
            self.relative_humidity,
            self.wind_speed,
            self.rainfall,
            self.pressure
        ]

        if all(param is None for param in weather_params):
            raise ValueError(
                'Observation must include at least one weather parameter '
                '(temperature, relative_humidity, wind_speed, rainfall, or pressure).'
            )

        return self


class ObservationCreate(ObservationBase):
    """Schema for creating a weather observation."""
    pass


class ObservationUpdate(BaseSchema):
    """Schema for updating weather observation."""
    temperature: Optional[float] = None
    relative_humidity: Optional[int] = Field(None, ge=0, le=100)
    wind_speed: Optional[float] = Field(None, ge=0)
    wind_direction: Optional[int] = Field(None, ge=0, le=360)
    rainfall: Optional[float] = Field(None, ge=0)
    pressure: Optional[float] = None


class Observation(ObservationBase, IDSchema, TimestampSchema):
    """Complete weather observation schema."""
    pass


# Response schemas (used by API endpoints)
StationResponse = Station
ObservationResponse = Observation


class WeatherQueryParams(BaseModel):
    """Query parameters for weather data requests."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=10000)
    offset: int = Field(0, ge=0)


# Daily Summary Schemas (for daily aggregates with min/max temps)

class DailySummaryBase(BaseSchema):
    """
    Base daily weather summary schema with separate min/max temperatures.

    Daily summaries aggregate weather data over 24-hour periods,
    providing min/max temperatures, mean humidity, and totals.
    """
    station_id: int
    date: DateType = Field(..., description="Observation date")

    # Temperature statistics
    temp_max: Optional[float] = Field(
        None,
        description="Maximum temperature in °C over 24-hour period"
    )
    temp_max_time: Optional[datetime] = Field(
        None,
        description="Time when maximum temperature was recorded"
    )
    temp_min: Optional[float] = Field(
        None,
        description="Minimum temperature in °C over 24-hour period"
    )
    temp_min_time: Optional[datetime] = Field(
        None,
        description="Time when minimum temperature was recorded"
    )

    # Precipitation
    rainfall_total: Optional[float] = Field(
        None,
        ge=0,
        description="Total 24-hour rainfall in mm"
    )

    # Other statistics
    mean_rh: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Mean relative humidity in % (average of 0600, 0900, 1200, 1500 observations)"
    )
    wind_speed: Optional[float] = Field(
        None,
        ge=0,
        description="Mean wind speed in m/s over 24-hour period (average of available readings)"
    )
    sunshine_hours: Optional[float] = Field(
        None,
        ge=0,
        le=24,
        description="Total sunshine duration in hours during the 24-hour period"
    )


class DailySummaryResponse(DailySummaryBase, IDSchema, TimestampSchema):
    """Complete daily summary response schema."""
    pass
