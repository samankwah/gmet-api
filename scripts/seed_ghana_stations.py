"""
Seed script for Ghana weather stations and location mappings.

This script populates the database with actual GMet weather stations across Ghana
and creates location mappings for user-friendly city-based queries.

Run this script after running database migrations:
    python -m scripts.seed_ghana_stations
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.weather_data import Station
from app.models.location import LocationMapping
from app.utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


# Ghana weather stations data
# Source: Ghana Meteorological Agency (GMet) - Major synoptic and climate stations
GHANA_STATIONS = [
    # Greater Accra Region
    {
        "name": "Kotoka International Airport",
        "code": "DGAA",
        "latitude": 5.6037,
        "longitude": -0.1870,
        "region": "Greater Accra",
        "locations": [
            {"name": "Accra", "type": "city", "primary": True},
            {"name": "Greater Accra", "type": "region", "primary": False},
            {"name": "ACC", "type": "alias", "primary": False},
        ]
    },

    # Ashanti Region
    {
        "name": "Kumasi Airport",
        "code": "DGSI",
        "latitude": 6.7146,
        "longitude": -1.5904,
        "region": "Ashanti",
        "locations": [
            {"name": "Kumasi", "type": "city", "primary": True},
            {"name": "Ashanti", "type": "region", "primary": False},
            {"name": "KMS", "type": "alias", "primary": False},
        ]
    },

    # Northern Region
    {
        "name": "Tamale Airport",
        "code": "DGLE",
        "latitude": 9.5572,
        "longitude": -0.8632,
        "region": "Northern",
        "locations": [
            {"name": "Tamale", "type": "city", "primary": True},
            {"name": "Northern", "type": "region", "primary": False},
            {"name": "TML", "type": "alias", "primary": False},
        ]
    },

    # Western Region
    {
        "name": "Takoradi Airport",
        "code": "DGTK",
        "latitude": 4.8960,
        "longitude": -1.7747,
        "region": "Western",
        "locations": [
            {"name": "Takoradi", "type": "city", "primary": True},
            {"name": "Sekondi-Takoradi", "type": "city", "primary": False},
            {"name": "Western", "type": "region", "primary": False},
            {"name": "TKD", "type": "alias", "primary": False},
        ]
    },

    # Central Region
    {
        "name": "Cape Coast Meteorological Station",
        "code": "DGCC",
        "latitude": 5.1054,
        "longitude": -1.2467,
        "region": "Central",
        "locations": [
            {"name": "Cape Coast", "type": "city", "primary": True},
            {"name": "Central", "type": "region", "primary": False},
            {"name": "CCT", "type": "alias", "primary": False},
        ]
    },

    # Eastern Region
    {
        "name": "Koforidua Meteorological Station",
        "code": "DGKF",
        "latitude": 6.0833,
        "longitude": -0.2500,
        "region": "Eastern",
        "locations": [
            {"name": "Koforidua", "type": "city", "primary": True},
            {"name": "Eastern", "type": "region", "primary": False},
            {"name": "KFD", "type": "alias", "primary": False},
        ]
    },

    # Volta Region
    {
        "name": "Ho Meteorological Station",
        "code": "DGHO",
        "latitude": 6.6000,
        "longitude": 0.4700,
        "region": "Volta",
        "locations": [
            {"name": "Ho", "type": "city", "primary": True},
            {"name": "Volta", "type": "region", "primary": False},
        ]
    },

    # Upper East Region
    {
        "name": "Bolgatanga Meteorological Station",
        "code": "DGBG",
        "latitude": 10.7833,
        "longitude": -0.8667,
        "region": "Upper East",
        "locations": [
            {"name": "Bolgatanga", "type": "city", "primary": True},
            {"name": "Upper East", "type": "region", "primary": False},
            {"name": "Bolga", "type": "alias", "primary": False},
        ]
    },

    # Upper West Region
    {
        "name": "Wa Meteorological Station",
        "code": "DGWA",
        "latitude": 10.0633,
        "longitude": -2.5078,
        "region": "Upper West",
        "locations": [
            {"name": "Wa", "type": "city", "primary": True},
            {"name": "Upper West", "type": "region", "primary": False},
        ]
    },

    # Brong-Ahafo Region
    {
        "name": "Sunyani Meteorological Station",
        "code": "DGSN",
        "latitude": 7.3383,
        "longitude": -2.3275,
        "region": "Brong-Ahafo",
        "locations": [
            {"name": "Sunyani", "type": "city", "primary": True},
            {"name": "Brong-Ahafo", "type": "region", "primary": False},
            {"name": "Bono", "type": "region", "primary": False},
        ]
    },

    # Additional Important Stations
    {
        "name": "Tema Meteorological Station",
        "code": "DGTM",
        "latitude": 5.6667,
        "longitude": 0.0167,
        "region": "Greater Accra",
        "locations": [
            {"name": "Tema", "type": "city", "primary": True},
        ]
    },

    {
        "name": "Saltpond Meteorological Station",
        "code": "DGSP",
        "latitude": 5.2000,
        "longitude": -1.0667,
        "region": "Central",
        "locations": [
            {"name": "Saltpond", "type": "city", "primary": True},
        ]
    },

    {
        "name": "Yendi Meteorological Station",
        "code": "DGYN",
        "latitude": 9.4333,
        "longitude": -0.0167,
        "region": "Northern",
        "locations": [
            {"name": "Yendi", "type": "city", "primary": True},
        ]
    },

    {
        "name": "Wenchi Meteorological Station",
        "code": "DGWN",
        "latitude": 7.7333,
        "longitude": -2.1000,
        "region": "Brong-Ahafo",
        "locations": [
            {"name": "Wenchi", "type": "city", "primary": True},
        ]
    },

    {
        "name": "Navrongo Meteorological Station",
        "code": "DGNV",
        "latitude": 10.9000,
        "longitude": -1.0833,
        "region": "Upper East",
        "locations": [
            {"name": "Navrongo", "type": "city", "primary": True},
        ]
    },
]


async def seed_stations():
    """Seed the database with Ghana weather stations and location mappings."""

    # Create async engine
    engine = create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=False,
    )

    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    logger.info("=" * 60)
    logger.info("Starting Ghana weather stations seeding process")
    logger.info("=" * 60)

    async with async_session() as session:
        try:
            stations_created = 0
            locations_created = 0

            for station_data in GHANA_STATIONS:
                # Check if station already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(Station).where(Station.code == station_data["code"])
                )
                existing_station = result.scalars().first()

                if existing_station:
                    logger.info(f"Station {station_data['code']} already exists, skipping...")
                    station = existing_station
                else:
                    # Create station
                    station = Station(
                        name=station_data["name"],
                        code=station_data["code"],
                        latitude=station_data["latitude"],
                        longitude=station_data["longitude"],
                        region=station_data["region"]
                    )
                    session.add(station)
                    await session.flush()  # Get the station ID
                    stations_created += 1
                    logger.info(f"✓ Created station: {station.name} ({station.code})")

                # Create location mappings
                for loc in station_data.get("locations", []):
                    # Check if mapping already exists
                    result = await session.execute(
                        select(LocationMapping).where(
                            LocationMapping.location_name == loc["name"],
                            LocationMapping.station_id == station.id
                        )
                    )
                    existing_mapping = result.scalars().first()

                    if not existing_mapping:
                        mapping = LocationMapping(
                            location_name=loc["name"],
                            location_type=loc["type"],
                            station_id=station.id,
                            is_primary=loc["primary"],
                            is_active=True
                        )
                        session.add(mapping)
                        locations_created += 1
                        logger.info(f"  ➜ Added location mapping: {loc['name']} -> {station.code}")

            # Commit all changes
            await session.commit()

            logger.info("=" * 60)
            logger.info(f"✓ Seeding completed successfully!")
            logger.info(f"  Stations created: {stations_created}")
            logger.info(f"  Location mappings created: {locations_created}")
            logger.info("=" * 60)

        except Exception as e:
            await session.rollback()
            logger.error(f"✗ Error during seeding: {e}")
            raise
        finally:
            await engine.dispose()


def main():
    """Main entry point for the seed script."""
    try:
        asyncio.run(seed_stations())
        logger.info("\n🎉 Ghana weather stations seeded successfully!")
        logger.info("You can now query locations like 'Accra', 'Kumasi', 'Tamale', etc.")

    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Seeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
