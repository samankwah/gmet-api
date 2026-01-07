"""
Data Migration Script: Migrate to Hybrid Weather Data Storage

This script migrates from single-table storage to hybrid storage:
- Backs up existing synoptic_observations data
- Truncates both daily_summaries and synoptic_observations tables
- Runs the new hybrid import to populate both tables correctly
- Verifies data integrity and generates migration report

Usage:
    python scripts/migrate_to_hybrid_storage.py
"""

import asyncio
import aiosqlite
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Import the new hybrid import function
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.import_hybrid_weather_data import import_hybrid_data

DB_PATH = "gmet_weather.db"
BACKUP_DIR = Path("backups")


async def backup_synoptic_observations(db: aiosqlite.Connection) -> str:
    """
    Backup existing synoptic_observations table to CSV.

    Returns:
        Path to backup file
    """
    print("\n" + "=" * 80)
    print("STEP 1: BACKUP EXISTING DATA")
    print("=" * 80)

    # Create backup directory if it doesn't exist
    BACKUP_DIR.mkdir(exist_ok=True)

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"synoptic_observations_backup_{timestamp}.csv"

    print(f"Backing up to: {backup_path}")

    # Count existing records
    async with db.execute("SELECT COUNT(*) FROM synoptic_observations") as cursor:
        count = await cursor.fetchone()
        record_count = count[0] if count else 0

    print(f"Records to backup: {record_count:,}")

    if record_count == 0:
        print("No records to backup. Skipping...")
        return str(backup_path)

    # Export to CSV
    async with db.execute("SELECT * FROM synoptic_observations") as cursor:
        columns = [description[0] for description in cursor.description]
        rows = await cursor.fetchall()

    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(backup_path, index=False)

    print(f"[OK] Backup complete: {len(df):,} records saved")
    print(f"[OK] File size: {backup_path.stat().st_size / 1024:.2f} KB")

    return str(backup_path)


async def backup_daily_summaries(db: aiosqlite.Connection) -> str:
    """
    Backup existing daily_summaries table to CSV (if any data exists).

    Returns:
        Path to backup file
    """
    print("\nBacking up daily_summaries table...")

    # Count existing records
    async with db.execute("SELECT COUNT(*) FROM daily_summaries") as cursor:
        count = await cursor.fetchone()
        record_count = count[0] if count else 0

    print(f"Records to backup: {record_count:,}")

    if record_count == 0:
        print("No records to backup. Skipping...")
        return ""

    # Generate backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"daily_summaries_backup_{timestamp}.csv"

    # Export to CSV
    async with db.execute("SELECT * FROM daily_summaries") as cursor:
        columns = [description[0] for description in cursor.description]
        rows = await cursor.fetchall()

    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(backup_path, index=False)

    print(f"[OK] Backup complete: {len(df):,} records saved")

    return str(backup_path)


async def truncate_tables(db: aiosqlite.Connection):
    """
    Truncate both daily_summaries and synoptic_observations tables.
    """
    print("\n" + "=" * 80)
    print("STEP 2: TRUNCATE TABLES")
    print("=" * 80)

    print("Truncating synoptic_observations...")
    await db.execute("DELETE FROM synoptic_observations")
    await db.commit()
    print("[OK] synoptic_observations truncated")

    print("Truncating daily_summaries...")
    await db.execute("DELETE FROM daily_summaries")
    await db.commit()
    print("[OK] daily_summaries truncated")


async def run_hybrid_import(csv_path: str = "gmet_synoptic_data.csv", year_start: int = 2024, year_end: int = 2025):
    """
    Run the new hybrid import script.
    """
    print("\n" + "=" * 80)
    print("STEP 3: RUN HYBRID IMPORT")
    print("=" * 80)

    await import_hybrid_data(csv_path, year_start, year_end)


async def verify_data_integrity(db: aiosqlite.Connection) -> Dict:
    """
    Verify data integrity after migration.

    Returns:
        Dictionary with verification results
    """
    print("\n" + "=" * 80)
    print("STEP 4: VERIFY DATA INTEGRITY")
    print("=" * 80)

    results = {}

    # Count synoptic observations
    async with db.execute("SELECT COUNT(*) FROM synoptic_observations") as cursor:
        count = await cursor.fetchone()
        synoptic_count = count[0] if count else 0
    results['synoptic_count'] = synoptic_count
    print(f"Synoptic observations: {synoptic_count:,}")

    # Count daily summaries
    async with db.execute("SELECT COUNT(*) FROM daily_summaries") as cursor:
        count = await cursor.fetchone()
        daily_count = count[0] if count else 0
    results['daily_count'] = daily_count
    print(f"Daily summaries: {daily_count:,}")

    # Get date range for synoptic observations
    async with db.execute(
        "SELECT MIN(obs_datetime), MAX(obs_datetime) FROM synoptic_observations"
    ) as cursor:
        date_range = await cursor.fetchone()
        if date_range:
            results['synoptic_start'] = date_range[0]
            results['synoptic_end'] = date_range[1]
            print(f"Synoptic date range: {date_range[0]} to {date_range[1]}")

    # Get date range for daily summaries
    async with db.execute(
        "SELECT MIN(date), MAX(date) FROM daily_summaries"
    ) as cursor:
        date_range = await cursor.fetchone()
        if date_range:
            results['daily_start'] = date_range[0]
            results['daily_end'] = date_range[1]
            print(f"Daily summary date range: {date_range[0]} to {date_range[1]}")

    # Count stations with data
    async with db.execute(
        "SELECT COUNT(DISTINCT station_id) FROM synoptic_observations"
    ) as cursor:
        count = await cursor.fetchone()
        synoptic_stations = count[0] if count else 0
    results['synoptic_stations'] = synoptic_stations
    print(f"Stations with synoptic data: {synoptic_stations}")

    async with db.execute(
        "SELECT COUNT(DISTINCT station_id) FROM daily_summaries"
    ) as cursor:
        count = await cursor.fetchone()
        daily_stations = count[0] if count else 0
    results['daily_stations'] = daily_stations
    print(f"Stations with daily summaries: {daily_stations}")

    # Sample data validation - check temp_max >= temp_min
    async with db.execute("""
        SELECT COUNT(*) FROM daily_summaries
        WHERE temp_max IS NOT NULL
        AND temp_min IS NOT NULL
        AND temp_max < temp_min
    """) as cursor:
        count = await cursor.fetchone()
        invalid_temps = count[0] if count else 0
    results['invalid_temp_ranges'] = invalid_temps
    if invalid_temps > 0:
        print(f"[WARNING] {invalid_temps} records with temp_max < temp_min!")
    else:
        print("[OK] All temperature ranges valid (temp_max >= temp_min)")

    # Check for NULL observation times
    async with db.execute("""
        SELECT COUNT(*) FROM synoptic_observations
        WHERE obs_datetime IS NULL
    """) as cursor:
        count = await cursor.fetchone()
        null_times = count[0] if count else 0
    results['null_obs_times'] = null_times
    if null_times > 0:
        print(f"[WARNING] {null_times} synoptic observations with NULL obs_datetime!")
    else:
        print("[OK] All synoptic observations have valid obs_datetime")

    # Check mean_rh range (0-100)
    async with db.execute("""
        SELECT COUNT(*) FROM daily_summaries
        WHERE mean_rh IS NOT NULL
        AND (mean_rh < 0 OR mean_rh > 100)
    """) as cursor:
        count = await cursor.fetchone()
        invalid_rh = count[0] if count else 0
    results['invalid_mean_rh'] = invalid_rh
    if invalid_rh > 0:
        print(f"[WARNING] {invalid_rh} records with mean_rh out of range (0-100)!")
    else:
        print("[OK] All mean_rh values within valid range (0-100)")

    # Get sample daily summary record
    async with db.execute("""
        SELECT s.code, ds.date, ds.temp_min, ds.temp_max, ds.mean_rh, ds.rainfall_total
        FROM daily_summaries ds
        JOIN stations s ON s.id = ds.station_id
        WHERE ds.temp_min IS NOT NULL AND ds.temp_max IS NOT NULL
        ORDER BY ds.date DESC
        LIMIT 1
    """) as cursor:
        sample = await cursor.fetchone()
        if sample:
            print(f"\nSample daily summary:")
            print(f"  Station: {sample[0]}, Date: {sample[1]}")
            print(f"  Temp min: {sample[2]}°C, Temp max: {sample[3]}°C")
            print(f"  Mean RH: {sample[4]}%, Rainfall: {sample[5]} mm")

    # Get sample synoptic observation
    async with db.execute("""
        SELECT s.code, so.obs_datetime, so.temperature, so.relative_humidity
        FROM synoptic_observations so
        JOIN stations s ON s.id = so.station_id
        WHERE so.temperature IS NOT NULL OR so.relative_humidity IS NOT NULL
        ORDER BY so.obs_datetime DESC
        LIMIT 1
    """) as cursor:
        sample = await cursor.fetchone()
        if sample:
            print(f"\nSample synoptic observation:")
            print(f"  Station: {sample[0]}, Time: {sample[1]}")
            print(f"  Temperature: {sample[2]}°C, RH: {sample[3]}%")

    return results


async def generate_migration_report(
    backup_path: str,
    daily_backup_path: str,
    verification_results: Dict
):
    """
    Generate migration report.
    """
    print("\n" + "=" * 80)
    print("MIGRATION REPORT")
    print("=" * 80)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_path = BACKUP_DIR / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(report_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("HYBRID WEATHER DATA STORAGE MIGRATION REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Migration Date: {timestamp}\n\n")

        f.write("BACKUPS CREATED:\n")
        f.write(f"  Synoptic observations: {backup_path}\n")
        if daily_backup_path:
            f.write(f"  Daily summaries: {daily_backup_path}\n")
        f.write("\n")

        f.write("DATA IMPORTED:\n")
        f.write(f"  Synoptic observations: {verification_results.get('synoptic_count', 0):,}\n")
        f.write(f"  Daily summaries: {verification_results.get('daily_count', 0):,}\n")
        f.write(f"  Stations with synoptic data: {verification_results.get('synoptic_stations', 0)}\n")
        f.write(f"  Stations with daily summaries: {verification_results.get('daily_stations', 0)}\n")
        f.write("\n")

        f.write("DATE RANGES:\n")
        f.write(f"  Synoptic: {verification_results.get('synoptic_start', 'N/A')} to {verification_results.get('synoptic_end', 'N/A')}\n")
        f.write(f"  Daily: {verification_results.get('daily_start', 'N/A')} to {verification_results.get('daily_end', 'N/A')}\n")
        f.write("\n")

        f.write("DATA VALIDATION:\n")
        f.write(f"  Invalid temp ranges (max < min): {verification_results.get('invalid_temp_ranges', 0)}\n")
        f.write(f"  NULL observation times: {verification_results.get('null_obs_times', 0)}\n")
        f.write(f"  Invalid mean_rh values: {verification_results.get('invalid_mean_rh', 0)}\n")
        f.write("\n")

        # Summary
        issues = (
            verification_results.get('invalid_temp_ranges', 0) +
            verification_results.get('null_obs_times', 0) +
            verification_results.get('invalid_mean_rh', 0)
        )

        if issues == 0:
            f.write("MIGRATION STATUS: [SUCCESS] No data integrity issues detected\n")
        else:
            f.write(f"MIGRATION STATUS: [WARNING] {issues} data integrity issues detected\n")

        f.write("\n" + "=" * 80 + "\n")

    print(f"\n[OK] Migration report saved to: {report_path}")


async def migrate():
    """
    Main migration function.
    """
    print("=" * 80)
    print("HYBRID WEATHER DATA STORAGE MIGRATION")
    print("=" * 80)
    print("\nThis script will:")
    print("  1. Backup existing data")
    print("  2. Truncate both tables")
    print("  3. Run hybrid import (2024-2025 data)")
    print("  4. Verify data integrity")
    print("  5. Generate migration report")
    print("\n" + "=" * 80)

    # Confirmation
    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # Step 1: Backup
        backup_path = await backup_synoptic_observations(db)
        daily_backup_path = await backup_daily_summaries(db)

        # Step 2: Truncate
        await truncate_tables(db)

    # Step 3: Import (opens its own connection)
    await run_hybrid_import()

    # Step 4 & 5: Verify and report
    async with aiosqlite.connect(DB_PATH) as db:
        verification_results = await verify_data_integrity(db)
        await generate_migration_report(backup_path, daily_backup_path, verification_results)

    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Restart the API server to use the new data")
    print("  2. Test API endpoints:")
    print("     - /v1/current?location=Tema")
    print("     - /v1/historical?station=Tema&start=2024-01-01&end=2024-12-31")
    print("     - /v1/historical?station=Tema&start=2024-01-01&end=2024-12-31&granularity=synoptic")
    print("     - /v1/daily-summaries/23024TEM?start=2024-01-01&end=2024-12-31")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(migrate())
