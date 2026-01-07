"""
Hybrid Weather Data Import Script

This script imports weather data from CSV into BOTH:
1. daily_summaries table - with separate temp_min, temp_max, mean_rh
2. synoptic_observations table - with time-specific readings

Preserves data granularity: min/max temps and time-specific humidity readings.
"""

import asyncio
import pandas as pd
from datetime import datetime, date, timezone
from collections import defaultdict
import aiosqlite
from typing import Dict, List, Tuple, Optional

CSV_PATH = "gmet_synoptic_data.csv"
DB_PATH = "gmet_weather.db"

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
    rh_values = []
    rr_values = []
    kts_values = []
    p_values = []
    sunhr_values = []

    # Extract values from day_data
    for element_time_key, obs in day_data.items():
        element = obs['element']
        value = obs['value']

        if element == ELEMENT_TX:
            tx_value = value
        elif element == ELEMENT_TN:
            tn_value = value
        elif element == ELEMENT_RH:
            # Collect all RH readings for mean calculation
            rh_values.append(value)
        elif element == ELEMENT_RR:
            rr_values.append(value)
        elif element == ELEMENT_KTS:
            kts_values.append(value)
        elif element == ELEMENT_P:
            p_values.append(value)
        elif element == ELEMENT_SUNHR:
            sunhr_values.append(value)

    # Skip if no meaningful data
    if not any([tx_value, tn_value, rh_values, rr_values, kts_values, sunhr_values]):
        return None

    # Build summary
    summary = {
        'date': date(year, month, day),
        'temp_max': tx_value,
        'temp_max_time': datetime(year, month, day, 9, 0, tzinfo=timezone.utc) if tx_value else None,
        'temp_min': tn_value,
        'temp_min_time': datetime(year, month, day, 9, 0, tzinfo=timezone.utc) if tn_value else None,
        'rainfall_total': sum(rr_values) if rr_values else None,
        'mean_rh': int(round(sum(rh_values) / len(rh_values))) if rh_values else None,
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
    print(f"Importing data from {year_start} to {year_end}")

    # Load CSV
    print(f"\nLoading CSV: {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Total rows: {len(df):,}")

    # Filter by year range
    df = df[(df['Year'] >= year_start) & (df['Year'] <= year_end)]
    print(f"Filtered to {year_start}-{year_end}: {len(df):,} rows")

    async with aiosqlite.connect(DB_PATH) as db:
        # Start transaction for data safety
        await db.execute("BEGIN TRANSACTION")

        try:
            # Get stations mapping
            print("\nFetching stations from database...")
            async with db.execute("SELECT id, code FROM stations") as cursor:
                stations = {code: sid async for sid, code in cursor}
            print(f"Found {len(stations)} stations")

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


async def insert_daily_summaries_batch(db: aiosqlite.Connection, batch: List[Dict], error_count: int = 0) -> int:
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
                 rainfall_total, mean_rh, wind_speed, sunshine_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary['station_id'],
                summary['date'].isoformat(),
                summary['temp_max'],
                summary['temp_max_time'].isoformat() if summary['temp_max_time'] else None,
                summary['temp_min'],
                summary['temp_min_time'].isoformat() if summary['temp_min_time'] else None,
                summary['rainfall_total'],
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


async def insert_synoptic_obs_batch(db: aiosqlite.Connection, batch: List[Dict], error_count: int = 0) -> int:
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
