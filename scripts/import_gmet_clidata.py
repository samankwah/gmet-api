"""
Import script for Ghana Meteorological Agency CLIDATA format.

This script parses the GMet CLIDATA CSV format and imports historical weather data
into the database. The CSV uses a wide format where each row represents one month
of data for a specific station, element (parameter), year, and time.

CSV Structure:
- Station ID: GMet internal station identifier (e.g., "23024TEM")
- Element ID: Weather parameter code (e.g., "Kts" for wind speed in knots)
- Year, Month, Time: Date components (e.g., "2013", "01", "09:00")
- Columns "01" through "31": Daily values for each day of the month
- Geogr1, Geogr2: Latitude and Longitude
- Name: Station name

Usage:
    python -m scripts.import_gmet_clidata <csv_file_path> [--dry-run] [--batch-size N]
"""

import asyncio
import csv
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.weather_data import Station, Observation
from app.utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


# Mapping from GMet Element IDs to database fields and conversion functions
ELEMENT_MAPPING: Dict[str, Tuple[str, callable]] = {
    "Kts": ("wind_speed", lambda x: float(x) * 0.514444),  # Knots to m/s
    "Temp": ("temperature", float),  # Temperature in Celsius
    "RH": ("humidity", float),  # Relative humidity percentage
    "Rain": ("rainfall", float),  # Rainfall in mm
    "Pressure": ("pressure", float),  # Pressure in hPa
    "WindDir": ("wind_direction", float),  # Wind direction in degrees
    # Add more mappings as needed
}

# Mapping from GMet Station IDs to database station codes
# This mapping should be updated based on actual GMet station data
STATION_ID_MAPPING: Dict[str, str] = {
    "23024TEM": "DGTM",  # Tema
    "23022SAL": "DGSP",  # Saltpond
    "23016ACC": "DGAA",  # Accra (KIAMO-Accra)
    "23003TDI": "DGTK",  # Takoradi
    "23002ADA": None,  # Ada (needs station code)
    "23001AXM": None,  # Axim (needs station code)
    # Add more mappings as needed
}


def parse_day_value(value: str) -> Optional[float]:
    """
    Parse a day value from the CSV.
    
    Handles empty strings, 0 values, and numeric strings.
    Returns None for missing/invalid data.
    """
    if not value or value == "" or value == "0":
        return None
    
    try:
        # Try to convert to float
        val = float(value)
        # Return None for 0 values (likely missing data)
        return None if val == 0 else val
    except (ValueError, TypeError):
        return None


def create_timestamp(year: str, month: str, day: int, time: str) -> datetime:
    """
    Create a timezone-aware datetime from date components.
    
    Args:
        year: Year as string (e.g., "2013")
        month: Month as string (e.g., "01")
        day: Day of month (1-31)
        time: Time as string (e.g., "09:00")
    
    Returns:
        datetime object with UTC timezone
    """
    try:
        # Parse time (format: "HH:MM")
        hour, minute = map(int, time.split(":"))
        
        # Create datetime
        dt = datetime(
            int(year),
            int(month),
            day,
            hour,
            minute,
            tzinfo=timezone.utc
        )
        return dt
    except (ValueError, AttributeError) as e:
        logger.error(f"Error parsing timestamp: year={year}, month={month}, day={day}, time={time}, error={e}")
        raise


async def get_or_create_station(
    db: AsyncSession,
    gmet_station_id: str,
    name: str,
    latitude: float,
    longitude: float
) -> Optional[Station]:
    """
    Get existing station or create a new one based on GMet station data.
    
    Args:
        db: Database session
        gmet_station_id: GMet internal station ID
        name: Station name
        latitude: Latitude
        longitude: Longitude
    
    Returns:
        Station object or None if unable to create/find
    """
    # First, try to find by mapped station code
    station_code = STATION_ID_MAPPING.get(gmet_station_id)
    
    if station_code:
        result = await db.execute(
            select(Station).where(Station.code == station_code)
        )
        station = result.scalar_one_or_none()
        if station:
            logger.debug(f"Found existing station: {station_code} ({name})")
            return station
    
    # Try to find by name (case-insensitive)
    result = await db.execute(
        select(Station).where(Station.name.ilike(f"%{name}%"))
    )
    station = result.scalar_one_or_none()
    
    if station:
        logger.debug(f"Found existing station by name: {station.code} ({name})")
        return station
    
    # If no mapping exists and station not found, log warning
    if not station_code:
        logger.warning(
            f"No station code mapping for GMet ID {gmet_station_id} ({name}). "
            f"Skipping observations for this station."
        )
        return None
    
    # Create new station if we have a code but station doesn't exist
    logger.info(f"Creating new station: {station_code} ({name})")
    station = Station(
        name=name,
        code=station_code,
        latitude=latitude,
        longitude=longitude,
        region="Unknown"  # Will need to be updated manually
    )
    db.add(station)
    await db.flush()
    return station


async def import_clidata_row(
    db: AsyncSession,
    row: Dict[str, str],
    dry_run: bool = False
) -> int:
    """
    Import a single row from the CLIDATA CSV.
    
    Each row represents one month of data for a specific station, element, year, and time.
    This function expands it into individual daily observations.
    
    Args:
        db: Database session
        row: CSV row as dictionary
        dry_run: If True, don't commit to database
    
    Returns:
        Number of observations created
    """
    station_id = row.get("Station ID", "").strip('"')
    element_id = row.get("Element ID", "").strip('"')
    year = row.get("Year", "").strip('"')
    month = row.get("Month", "").strip('"')
    time = row.get("Time", "").strip('"')
    name = row.get("Name", "").strip('"')
    
    # Get latitude and longitude
    try:
        latitude = float(row.get("Geogr1", "0").strip('"'))
        longitude = float(row.get("Geogr2", "0").strip('"'))
    except (ValueError, TypeError):
        logger.warning(f"Invalid coordinates for {station_id}: Geogr1={row.get('Geogr1')}, Geogr2={row.get('Geogr2')}")
        return 0
    
    # Check if we have a mapping for this element
    if element_id not in ELEMENT_MAPPING:
        logger.debug(f"Skipping unknown element: {element_id}")
        return 0
    
    field_name, converter = ELEMENT_MAPPING[element_id]
    
    # Get or create station
    station = await get_or_create_station(
        db, station_id, name, latitude, longitude
    )
    
    if not station:
        return 0
    
    # Process each day of the month
    observations_created = 0
    day_columns = [f"{i:02d}" for i in range(1, 32)]  # "01" through "31"
    
    for day_str in day_columns:
        day = int(day_str)
        day_value = row.get(day_str, "").strip('"')
        
        # Parse the value
        value = parse_day_value(day_value)
        if value is None:
            continue  # Skip missing data
        
        # Convert value using the converter function
        try:
            converted_value = converter(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Error converting value {value} for {element_id}: {e}")
            continue
        
        # Create timestamp
        try:
            timestamp = create_timestamp(year, month, day, time)
        except Exception as e:
            logger.warning(f"Error creating timestamp: {e}")
            continue
        
        # Check if observation already exists
        result = await db.execute(
            select(Observation).where(
                Observation.station_id == station.id,
                Observation.timestamp == timestamp
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing observation
            setattr(existing, field_name, converted_value)
            logger.debug(f"Updated observation: {station.code} {timestamp} {field_name}={converted_value}")
        else:
            # Create new observation
            observation_data = {
                "station_id": station.id,
                "timestamp": timestamp,
                field_name: converted_value
            }
            observation = Observation(**observation_data)
            db.add(observation)
            observations_created += 1
            logger.debug(f"Created observation: {station.code} {timestamp} {field_name}={converted_value}")
    
    # Don't commit here - let the batch processing handle commits
    return observations_created


async def import_clidata_file(
    csv_file_path: str,
    dry_run: bool = False,
    batch_size: int = 1000
) -> Dict[str, int]:
    """
    Import CLIDATA CSV file into the database.
    
    Args:
        csv_file_path: Path to the CSV file
        dry_run: If True, don't commit to database
        batch_size: Number of rows to process before committing
    
    Returns:
        Dictionary with import statistics
    """
    stats = {
        "rows_processed": 0,
        "observations_created": 0,
        "observations_updated": 0,
        "errors": 0,
        "stations_found": set(),
        "elements_processed": set()
    }
    
    # Create database engine and session
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    logger.info(f"Starting CLIDATA import from: {csv_file_path}")
    logger.info(f"Dry run: {dry_run}, Batch size: {batch_size}")
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            async with async_session() as db:
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
                    try:
                        element_id = row.get("Element ID", "").strip('"')
                        station_id = row.get("Station ID", "").strip('"')
                        
                        stats["elements_processed"].add(element_id)
                        stats["rows_processed"] += 1
                        
                        observations = await import_clidata_row(db, row, dry_run)
                        stats["observations_created"] += observations
                        
                        if observations > 0:
                            station_code = STATION_ID_MAPPING.get(station_id, "Unknown")
                            stats["stations_found"].add(station_code)
                        
                        # Commit in batches
                        if not dry_run and row_num % batch_size == 0:
                            await db.commit()
                            logger.info(
                                f"Processed {row_num} rows, "
                                f"created {stats['observations_created']} observations"
                            )
                        elif not dry_run:
                            # Flush to ensure objects are in session for next batch
                            await db.flush()
                    
                    except Exception as e:
                        stats["errors"] += 1
                        logger.error(f"Error processing row {row_num}: {e}", exc_info=True)
                        if not dry_run:
                            await db.rollback()
                
                # Final commit
                if not dry_run:
                    await db.commit()
                    logger.info("Final commit completed")
    
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_file_path}")
        raise
    except Exception as e:
        logger.error(f"Error importing CLIDATA file: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()
    
    # Convert sets to lists for JSON serialization
    stats["stations_found"] = list(stats["stations_found"])
    stats["elements_processed"] = list(stats["elements_processed"])
    
    return stats


async def main():
    """Main entry point for the import script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Import GMet CLIDATA CSV file into database"
    )
    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to the CLIDATA CSV file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process without committing to database"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of rows to process before committing (default: 1000)"
    )
    
    args = parser.parse_args()
    
    # Validate file exists
    if not Path(args.csv_file).exists():
        logger.error(f"File not found: {args.csv_file}")
        sys.exit(1)
    
    try:
        stats = await import_clidata_file(
            args.csv_file,
            dry_run=args.dry_run,
            batch_size=args.batch_size
        )
        
        logger.info("=" * 60)
        logger.info("Import Statistics:")
        logger.info(f"  Rows processed: {stats['rows_processed']}")
        logger.info(f"  Observations created: {stats['observations_created']}")
        logger.info(f"  Errors: {stats['errors']}")
        logger.info(f"  Stations found: {len(stats['stations_found'])}")
        logger.info(f"  Elements processed: {', '.join(stats['elements_processed'])}")
        logger.info("=" * 60)
        
        if args.dry_run:
            logger.info("DRY RUN - No data was committed to database")
    
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

