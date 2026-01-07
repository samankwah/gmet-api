"""
Location mapping database model.

This module contains the LocationMapping model for mapping city/region names
to weather stations, enabling user-friendly location-based queries.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class LocationMapping(BaseModel):
    """
    Location mapping model.

    Maps human-readable location names (cities, regions, areas) to weather stations.
    This enables users to query by familiar names like "Accra" instead of station codes.

    Multiple location names can map to the same station (e.g., "Accra", "Greater Accra", "ACC").
    """

    __tablename__ = "location_mappings"

    location_name = Column(
        String(200),
        nullable=False,
        index=True,
        comment="Human-readable location name (e.g., 'Accra', 'Kumasi')"
    )

    location_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of location: 'city', 'region', 'district', 'alias'"
    )

    station_id = Column(
        Integer,
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the associated weather station"
    )

    is_primary = Column(
        Boolean,
        default=False,
        comment="Whether this is the primary name for the station"
    )

    is_active = Column(
        Boolean,
        default=True,
        comment="Whether this mapping is currently active"
    )

    # Relationship to station
    station = relationship("Station", backref="location_mappings")

    # Create composite indexes for efficient queries
    __table_args__ = (
        Index('idx_location_name_type', 'location_name', 'location_type'),
        Index('idx_location_active', 'is_active', 'location_name'),
    )

    def __repr__(self):
        return f"<LocationMapping(location_name='{self.location_name}', station_id={self.station_id})>"
