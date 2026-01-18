"""
Hybrid Weather Data Import Script

This script imports weather data from CSV into BOTH:
1. daily_summaries table - with separate temp_min, temp_max, mean_rh
2. synoptic_observations table - with time-specific readings

Preserves data granularity: min/max temps and time-specific humidity readings.

Supports both SQLite (local dev) and PostgreSQL (production) databases.
"""

import asyncio
import os
import sys
import pandas as pd
from datetime import datetime, date, timezone
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

CSV_PATH = "gmet_synoptic_data.csv"

# Determine database type from environment
def get_db_uri():
    """Get database URI from environment or settings."""
    db_uri = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
    if db_uri:
        return db_uri
    # Fall back to app settings
    try:
        from app.config import settings
        return settings.SQLALCHEMY_DATABASE_URI
    except ImportError:
        return "sqlite+aiosqlite:///gmet_weather.db"

DB_URI = get_db_uri()
IS_POSTGRES = 'postgresql' in DB_URI or 'postgres' in DB_URI

# Mapping from CSV station codes to database station codes (ICAO)
# CSV uses GMet internal codes, database uses ICAO codes
CSV_TO_DB_STATION_MAP = {
    '23016ACC': 'DGAA',   # Accra (Kotoka Airport)
    '23024TEM': 'DGTM',   # Tema
    '17009KSI': 'DGSI',   # Kumasi Airport
    '07006TLE': 'DGLE',   # Tamale Airport
    '23003TDI': 'DGTK',   # Takoradi Airport
    '23022SAL': 'DGSP',   # Saltpond
    '07000BOL': 'DGBG',   # Bolgatanga
    '04003NAV': 'DGNV',   # Navrongo
    '01013WA-': 'DGWA',   # Wa
    '01032SUN': 'DGSN',   # Sunyani
    '07017HO-': 'DGHO',   # Ho (using first Ho entry)
    '07058HO-': 'DGHO',   # Ho (alternate - maps to same station)
    '22050KDA': 'DGKF',   # Koforidua
    '08010YDI': 'DGYN',   # Yendi
    '01018WEN': 'DGWN',   # Wenchi
    '23001AXM': 'DGCC',   # Axim -> Cape Coast (nearest)
    # Stations without direct DB match (could add later):
    # '07003AKU': None,   # Akuse
    # '07008KRA': None,   # Krachie
    # '14067ABE': None,   # Abetifi
    # '15076AKA': None,   # Akatsi
    # '16015BEK': None,   # Bekwai
    # '21088ODA': None,   # Oda
    # '23002ADA': None,   # Ada
}

# Element type constants
ELEMENT_TX = 'Tx'  # Maximum temperature
ELEMENT_TN = 'Tn'  # Minimum temperature
ELEMENT_RH = 'RH'  # Relative humidity
ELEMENT_RR = 'RR'  # Rainfall
ELEMENT_KTS = 'Kts'  # Wind speed in knots
ELEMENT_P = 'P'  # Pressure
ELEMENT_SUNHR = 'SUNHR'  # Sunshine hours


def parse_time_to_hour(time_str: str) -> int:
    """
    Parse time string to hour integer.

    Args:
        time_str: Time string like "9:00", "15:00"

    Returns:
        Hour as integer (0-23)
    """
    if pd.isna(time_str):
        return 12  # Default to noon

    # Handle various formats: "9:00", "09:00", "9", etc.
    time_str = str(time_str).strip()
    if ':' in time_str:
        hour_str = time_str.split(':')[0]
    else:
        hour_str = time_str

    try:
        hour = int(float(hour_str))
        return hour if 0 <= hour <= 23 else 12
    except (ValueError, TypeError):
        return 12


def build_day_data_structure(group_df: pd.DataFrame) -> Dict[int, Dict]:
    """
    Build data structure: {day: {element_time: {element: value, time: hour}}}

    Args:
        group_df: DataFrame for one station/year/month

    Returns:
        Dictionary mapping day number to observations
    """
    days_data = defaultdict(lambda: defaultdict(dict))

    for _, row in group_df.iterrows():
        element = row["Element ID"]
        time_str = row["Time"]
        obs_hour = parse_time_to_hour(time_str)

        # Process each day column (1-31)
        for day in range(1, 32):
            col_name = str(day)
            if col_name not in row or pd.isna(row[col_name]):
                continue

            try:
                value = float(row[col_name])

                # Create unique key for (element, time) combination
                element_time_key = f"{element}_{obs_hour:02d}"

                days_data[day][element_time_key] = {
                    'element': element,
                    'value': value,
                    'hour': obs_hour
                }
            except (ValueError, TypeError):
                continue

    return days_data


def build_daily_summary(year: int, month: int, day: int, day_data: Dict) -> Optional[Dict]:
    """
    Build daily summary record from day's observations.

    Args:
        year, month, day: Date components
        day_data: Dictionary of observations for the day

    Returns:
        Dictionary with daily summary fields or None if no data
    """
    tx_value = None
    tn_value = None
    rh_by_hour = {}  # Store RH readings by hour: {6: value, 9: value, 12: value, 15: value}
    rr_values = []
    kts_values = []
    p_values = []
    sunhr_values = []

    # Extract values from day_data
    for element_time_key, obs in day_data.items():
        element = obs['element']
        value = obs['value']
        hour = obs['hour']

        if element == ELEMENT_TX:
            tx_value = value
        elif element == ELEMENT_TN:
            tn_value = value
        elif element == ELEMENT_RH:
            # Store RH reading by observation hour
            rh_by_hour[hour] = int(min(100, max(0, value)))
        elif element == ELEMENT_RR:
            rr_values.append(value)
        elif element == ELEMENT_KTS:
            kts_values.append(value)
        elif element == ELEMENT_P:
            p_values.append(value)
        elif element == ELEMENT_SUNHR:
            sunhr_values.append(value)

    # Skip if no meaningful data
    if not any([tx_value, tn_value, rh_by_hour, rr_values, kts_values, sunhr_values]):
        return None

    # Validate date before creating summary
    try:
        obs_date = date(year, month, day)
    except ValueError:
        # Invalid date (e.g., Feb 30, Apr 31) - skip this entry
        return None

    # Build summary
    obs_datetime = datetime(year, month, day, 9, 0, tzinfo=timezone.utc)
    summary = {
        'date': obs_date,
        'temp_max': tx_value,
        'temp_max_time': obs_datetime if tx_value else None,
        'temp_min': tn_value,
        'temp_min_time': obs_datetime if tn_value else None,
        'rainfall_total': sum(rr_values) if rr_values else None,

        # Individual RH readings at SYNOP times
        'rh_0600': rh_by_hour.get(6),
        'rh_0900': rh_by_hour.get(9),
        'rh_1200': rh_by_hour.get(12),
        'rh_1500': rh_by_hour.get(15),

        # Mean RH for backward compatibility
        'mean_rh': int(round(sum(rh_by_hour.values()) / len(rh_by_hour))) if rh_by_hour else None,

        'wind_speed': round(sum(kts_values) / len(kts_values) * 0.514444, 2) if kts_values else None,  # Convert knots to m/s (mean)
        'sunshine_hours': round(sum(sunhr_values) / len(sunhr_values), 1) if sunhr_values else None
    }

    return summary


def build_synoptic_observations(year: int, month: int, day: int, day_data: Dict) -> List[Dict]:
    """
    Build synoptic observation records for different observation times.

    Args:
        year, month, day: Date components
        day_data: Dictionary of observations for the day

    Returns:
        List of synoptic observation dictionaries
    """
    observations = []

    # Group by observation hour
    hour_observations = defaultdict(dict)

    for element_time_key, obs in day_data.items():
        element = obs['element']
        value = obs['value']
        hour = obs['hour']

        if element == ELEMENT_RH:
            hour_observations[hour]['relative_humidity'] = int(min(100, max(0, value)))
        elif element == ELEMENT_TX or element == ELEMENT_TN:
            # Store temps, will average if both exist
            if 'temperatures' not in hour_observations[hour]:
                hour_observations[hour]['temperatures'] = []
            hour_observations[hour]['temperatures'].append(value)
        elif element == ELEMENT_RR:
            hour_observations[hour]['rainfall'] = value
        elif element == ELEMENT_KTS:
            hour_observations[hour]['wind_speed'] = round(value * 0.514444, 2)
        elif element == ELEMENT_P:
            hour_observations[hour]['pressure'] = value

    # Create observation record for each hour
    for hour, fields in hour_observations.items():
        try:
            obs_dt = datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)

            observation = {
                'obs_datetime': obs_dt,
            }

            # Add temperature (average if both Tx and Tn exist)
            if 'temperatures' in fields:
                temps = fields['temperatures']
                observation['temperature'] = sum(temps) / len(temps)

            # Add other fields if present
            if 'relative_humidity' in fields:
                observation['relative_humidity'] = fields['relative_humidity']
            if 'rainfall' in fields:
                observation['rainfall'] = fields['rainfall']
            if 'wind_speed' in fields:
                observation['wind_speed'] = fields['wind_speed']
            if 'pressure' in fields:
                observation['pressure'] = fields['pressure']

            # Only add if has at least one weather parameter
            if len(observation) > 1:  # More than just obs_datetime
                observations.append(observation)

        except ValueError:
            # Invalid date (e.g., Feb 31)
            continue

    return observations


async def import_hybrid_data(csv_path: str = CSV_PATH, year_start: int = 2024, year_end: int = 2025):
    """
    Main import function - populates both daily_summaries and synoptic_observations.

    Args:
        csv_path: Path to CSV file
        year_start: Start year for import
        year_end: End year for import
    """
    print("=" * 80)
    print("HYBRID WEATHER DATA IMPORT")
    print("=" * 80)
    print(f"Database: {'PostgreSQL' if IS_POSTGRES else 'SQLite'}")
    print(f"Importing data from {year_start} to {year_end}")

    # Load CSV
    print(f"\nLoading CSV: {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Total rows: {len(df):,}")
    unique_stations = df['Station ID'].nunique()
    print(f"Unique stations in CSV: {unique_stations}")

    # Filter by year range
    df = df[(df['Year'] >= year_start) & (df['Year'] <= year_end)]
    print(f"Filtered to {year_start}-{year_end}: {len(df):,} rows")

    if IS_POSTGRES:
        await import_to_postgres(df)
    else:
        await import_to_sqlite(df)


async def import_to_postgres(df: pd.DataFrame):
    """Import data to PostgreSQL database."""
    import asyncpg

    # Convert asyncpg URL format
    db_url = DB_URI
    if db_url.startswith('postgresql+asyncpg://'):
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    elif db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://')

    conn = await asyncpg.connect(db_url)

    try:
        # Get stations mapping
        print("\nFetching stations from database...")
        rows = await conn.fetch("SELECT id, code FROM stations")
        db_stations = {row['code']: row['id'] for row in rows}
        print(f"Found {len(db_stations)} stations in database")

        # Create mapping from CSV station codes to database station IDs
        stations = {}
        mapped_count = 0
        for csv_code, db_code in CSV_TO_DB_STATION_MAP.items():
            if db_code in db_stations:
                stations[csv_code] = db_stations[db_code]
                mapped_count += 1
        print(f"Mapped {mapped_count} CSV station codes to database stations")

        # Group by station, year, month
        grouped = df.groupby(['Station ID', 'Year', 'Month'])
        total_groups = len(grouped)
        processed_groups = 0

        daily_summaries_created = 0
        synoptic_obs_created = 0
        error_count = 0

        # Batch storage
        daily_summaries_batch = []
        synoptic_obs_batch = []
        batch_size = 500  # Smaller batch for PostgreSQL

        print(f"\nProcessing {total_groups} station-month groups...")
        print("-" * 80)

        for (station_code, year, month), group_df in grouped:
            processed_groups += 1

            station_id = stations.get(station_code)
            if not station_id:
                continue

            # Build day-by-day data structure
            days_data = build_day_data_structure(group_df)

            # Process each day
            for day, day_data in days_data.items():
                # Create daily summary
                daily_summary = build_daily_summary(year, month, day, day_data)
                if daily_summary:
                    daily_summary['station_id'] = station_id
                    daily_summaries_batch.append(daily_summary)
                    daily_summaries_created += 1

                # Create synoptic observations
                synoptic_obs = build_synoptic_observations(year, month, day, day_data)
                for obs in synoptic_obs:
                    obs['station_id'] = station_id
                    synoptic_obs_batch.append(obs)
                    synoptic_obs_created += 1

            # Batch insert daily summaries
            if len(daily_summaries_batch) >= batch_size:
                error_count = await insert_daily_summaries_batch_pg(conn, daily_summaries_batch, error_count)
                daily_summaries_batch = []

            # Batch insert synoptic observations
            if len(synoptic_obs_batch) >= batch_size:
                error_count = await insert_synoptic_obs_batch_pg(conn, synoptic_obs_batch, error_count)
                synoptic_obs_batch = []

            # Progress update
            if processed_groups % 50 == 0:
                print(f"  Progress: {processed_groups}/{total_groups} groups")
                print(f"    Daily summaries: {daily_summaries_created:,}")
                print(f"    Synoptic observations: {synoptic_obs_created:,}")

        # Insert remaining batches
        if daily_summaries_batch:
            error_count = await insert_daily_summaries_batch_pg(conn, daily_summaries_batch, error_count)
        if synoptic_obs_batch:
            error_count = await insert_synoptic_obs_batch_pg(conn, synoptic_obs_batch, error_count)

        print("\n" + "=" * 80)
        print("IMPORT COMPLETE!")
        print("=" * 80)
        print(f"Processed: {processed_groups}/{total_groups} station-month groups")
        print(f"Daily summaries created: {daily_summaries_created:,}")
        print(f"Synoptic observations created: {synoptic_obs_created:,}")
        if error_count > 0:
            print(f"Errors encountered: {error_count} (see details above)")
        print("=" * 80)

    finally:
        await conn.close()


async def import_to_sqlite(df: pd.DataFrame):
    """Import data to SQLite database."""
    import aiosqlite

    db_path = "gmet_weather.db"
    if DB_URI.startswith('sqlite'):
        # Extract path from URI like sqlite+aiosqlite:///path.db
        db_path = DB_URI.split('///')[-1] if '///' in DB_URI else "gmet_weather.db"

    async with aiosqlite.connect(db_path) as db:
        # Start transaction for data safety
        await db.execute("BEGIN TRANSACTION")

        try:
            # Get stations mapping
            print("\nFetching stations from database...")
            async with db.execute("SELECT id, code FROM stations") as cursor:
                db_stations = {code: sid async for sid, code in cursor}
            print(f"Found {len(db_stations)} stations in database")

            # Create mapping from CSV station codes to database station IDs
            stations = {}
            mapped_count = 0
            for csv_code, db_code in CSV_TO_DB_STATION_MAP.items():
                if db_code in db_stations:
                    stations[csv_code] = db_stations[db_code]
                    mapped_count += 1
            print(f"Mapped {mapped_count} CSV station codes to database stations")

            # Group by station, year, month
            grouped = df.groupby(['Station ID', 'Year', 'Month'])
            total_groups = len(grouped)
            processed_groups = 0

            daily_summaries_created = 0
            synoptic_obs_created = 0
            error_count = 0

            # Batch storage
            daily_summaries_batch = []
            synoptic_obs_batch = []
            batch_size = 1000

            print(f"\nProcessing {total_groups} station-month groups...")
            print("-" * 80)

            for (station_code, year, month), group_df in grouped:
                processed_groups += 1

                station_id = stations.get(station_code)
                if not station_id:
                    continue

                # Build day-by-day data structure
                days_data = build_day_data_structure(group_df)

                # Process each day
                for day, day_data in days_data.items():
                    # Create daily summary
                    daily_summary = build_daily_summary(year, month, day, day_data)
                    if daily_summary:
                        daily_summary['station_id'] = station_id
                        daily_summaries_batch.append(daily_summary)
                        daily_summaries_created += 1

                    # Create synoptic observations
                    synoptic_obs = build_synoptic_observations(year, month, day, day_data)
                    for obs in synoptic_obs:
                        obs['station_id'] = station_id
                        synoptic_obs_batch.append(obs)
                        synoptic_obs_created += 1

                # Batch insert daily summaries
                if len(daily_summaries_batch) >= batch_size:
                    error_count = await insert_daily_summaries_batch(db, daily_summaries_batch, error_count)
                    daily_summaries_batch = []

                # Batch insert synoptic observations
                if len(synoptic_obs_batch) >= batch_size:
                    error_count = await insert_synoptic_obs_batch(db, synoptic_obs_batch, error_count)
                    synoptic_obs_batch = []

                # Progress update
                if processed_groups % 50 == 0:
                    print(f"  Progress: {processed_groups}/{total_groups} groups")
                    print(f"    Daily summaries: {daily_summaries_created:,}")
                    print(f"    Synoptic observations: {synoptic_obs_created:,}")

            # Insert remaining batches
            if daily_summaries_batch:
                error_count = await insert_daily_summaries_batch(db, daily_summaries_batch, error_count)
            if synoptic_obs_batch:
                error_count = await insert_synoptic_obs_batch(db, synoptic_obs_batch, error_count)

            # Commit transaction
            await db.commit()

            print("\n" + "=" * 80)
            print("IMPORT COMPLETE!")
            print("=" * 80)
            print(f"Processed: {processed_groups}/{total_groups} station-month groups")
            print(f"Daily summaries created: {daily_summaries_created:,}")
            print(f"Synoptic observations created: {synoptic_obs_created:,}")
            if error_count > 0:
                print(f"Errors encountered: {error_count} (see details above)")
            print("=" * 80)

        except Exception as e:
            # Rollback on error
            await db.rollback()
            print(f"\n{'=' * 80}")
            print("ERROR: Import failed!")
            print(f"{'=' * 80}")
            print(f"Error: {e}")
            print("Database rolled back to previous state.")
            print(f"{'=' * 80}")
            raise


# PostgreSQL batch insert functions using executemany for speed
async def insert_daily_summaries_batch_pg(conn, batch: List[Dict], error_count: int = 0) -> int:
    """Insert batch of daily summaries to PostgreSQL using executemany."""
    if not batch:
        return error_count

    try:
        # Prepare data as list of tuples
        records = [
            (
                summary['station_id'],
                summary['date'],
                summary['temp_max'],
                summary['temp_max_time'],
                summary['temp_min'],
                summary['temp_min_time'],
                summary['rainfall_total'],
                summary['rh_0600'],
                summary['rh_0900'],
                summary['rh_1200'],
                summary['rh_1500'],
                summary['mean_rh'],
                summary['wind_speed'],
                summary['sunshine_hours']
            )
            for summary in batch
        ]

        await conn.executemany("""
            INSERT INTO daily_summaries
            (station_id, date, temp_max, temp_max_time, temp_min, temp_min_time,
             rainfall_total, rh_0600, rh_0900, rh_1200, rh_1500, mean_rh, wind_speed, sunshine_hours)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (station_id, date) DO NOTHING
        """, records)

    except Exception as e:
        error_count += 1
        print(f"Error in batch insert of daily summaries: {e}")
        if error_count > 10:
            raise RuntimeError(f"Too many batch errors ({error_count}), aborting import")

    return error_count


async def insert_synoptic_obs_batch_pg(conn, batch: List[Dict], error_count: int = 0) -> int:
    """Insert batch of synoptic observations to PostgreSQL using executemany."""
    if not batch:
        return error_count

    try:
        # Prepare data as list of tuples with consistent columns
        records = [
            (
                obs['station_id'],
                obs['obs_datetime'],
                obs.get('temperature'),
                obs.get('relative_humidity'),
                obs.get('rainfall'),
                obs.get('wind_speed'),
                obs.get('pressure')
            )
            for obs in batch
        ]

        await conn.executemany("""
            INSERT INTO synoptic_observations
            (station_id, obs_datetime, temperature, relative_humidity, rainfall, wind_speed, pressure)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (station_id, obs_datetime) DO NOTHING
        """, records)

    except Exception as e:
        error_count += 1
        print(f"Error in batch insert of synoptic observations: {e}")
        if error_count > 10:
            raise RuntimeError(f"Too many batch errors ({error_count}), aborting import")

    return error_count


# SQLite batch insert functions
async def insert_daily_summaries_batch(db, batch: List[Dict], error_count: int = 0) -> int:
    """
    Insert batch of daily summaries.

    Args:
        db: Database connection
        batch: List of daily summary dictionaries
        error_count: Current error count

    Returns:
        Updated error count

    Raises:
        RuntimeError: If error count exceeds 100 (fail-fast)
    """
    for summary in batch:
        try:
            await db.execute("""
                INSERT OR IGNORE INTO daily_summaries
                (station_id, date, temp_max, temp_max_time, temp_min, temp_min_time,
                 rainfall_total, rh_0600, rh_0900, rh_1200, rh_1500, mean_rh, wind_speed, sunshine_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary['station_id'],
                summary['date'].isoformat(),
                summary['temp_max'],
                summary['temp_max_time'].isoformat() if summary['temp_max_time'] else None,
                summary['temp_min'],
                summary['temp_min_time'].isoformat() if summary['temp_min_time'] else None,
                summary['rainfall_total'],
                summary['rh_0600'],
                summary['rh_0900'],
                summary['rh_1200'],
                summary['rh_1500'],
                summary['mean_rh'],
                summary['wind_speed'],
                summary['sunshine_hours']
            ))
        except Exception as e:
            error_count += 1
            print(f"Error inserting daily summary: {e}")
            if error_count > 100:
                raise RuntimeError(f"Too many errors ({error_count}), aborting import")
            continue

    return error_count


async def insert_synoptic_obs_batch(db, batch: List[Dict], error_count: int = 0) -> int:
    """
    Insert batch of synoptic observations.

    Args:
        db: Database connection
        batch: List of synoptic observation dictionaries
        error_count: Current error count

    Returns:
        Updated error count

    Raises:
        RuntimeError: If error count exceeds 100 (fail-fast)
    """
    for obs in batch:
        try:
            # Build dynamic SQL based on available fields
            fields = ['station_id', 'obs_datetime']
            values = [obs['station_id'], obs['obs_datetime'].isoformat()]

            if 'temperature' in obs:
                fields.append('temperature')
                values.append(obs['temperature'])
            if 'relative_humidity' in obs:
                fields.append('relative_humidity')
                values.append(obs['relative_humidity'])
            if 'rainfall' in obs:
                fields.append('rainfall')
                values.append(obs['rainfall'])
            if 'wind_speed' in obs:
                fields.append('wind_speed')
                values.append(obs['wind_speed'])
            if 'pressure' in obs:
                fields.append('pressure')
                values.append(obs['pressure'])

            placeholders = ', '.join(['?' for _ in values])
            field_list = ', '.join(fields)

            await db.execute(
                f"INSERT OR IGNORE INTO synoptic_observations ({field_list}) VALUES ({placeholders})",
                values
            )
        except Exception as e:
            error_count += 1
            print(f"Error inserting synoptic observation: {e}")
            if error_count > 100:
                raise RuntimeError(f"Too many errors ({error_count}), aborting import")
            continue

    return error_count


if __name__ == "__main__":
    asyncio.run(import_hybrid_data())
