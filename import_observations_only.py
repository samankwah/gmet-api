"""
Import only observations from CSV (stations already exist in database).

This script imports observation data from the CSV file into the existing
database with 663 stations already loaded.
"""

import asyncio
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Database configuration
CSV_PATH = "gmet_synoptic_data.csv"
DB_URL = "sqlite+aiosqlite:///gmet_weather.db"

async def import_observations():
    """Import observations from CSV for existing stations."""
    print("=" * 80)
    print("GMET OBSERVATIONS IMPORT")
    print("=" * 80)

    # Load CSV
    print(f"\nLoading CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df):,} rows")

    # Connect to database
    engine = create_async_engine(DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get station code to ID mapping
        print("\nFetching stations from database...")
        result = await session.execute(text("SELECT id, code FROM stations"))
        stations = {code: station_id for station_id, code in result}
        print(f"Found {len(stations)} stations in database")

        # Check for existing checkpoint
        result = await session.execute(text("SELECT value FROM import_checkpoints WHERE key = 'last_group'"))
        last_group = result.scalar_one_or_none()

        if last_group:
            print(f"\nResuming from checkpoint: {last_group}")
        else:
            print("\nStarting fresh import...")

        # Process observations grouped by station, year, month
        grouped = df.groupby(["Station ID", "Year", "Month"])
        total_groups = len(grouped)
        processed = 0
        imported = 0
        skipped = 0

        print(f"\nProcessing {total_groups:,} station-month groups...")
        print("This will take several minutes...\n")

        for (station_code, year, month), group in grouped:
            processed += 1

            # Skip if already processed
            group_key = f"{station_code}-{year}-{month}"
            if last_group and group_key <= last_group:
                continue

            # Get station ID
            station_id = stations.get(station_code)
            if not station_id:
                skipped += 1
                continue

            # Process each row (element) in this month
            for _, row in group.iterrows():
                element = row["Element ID"]

                # Process each day of the month
                for day in range(1, 32):
                    col = str(day)
                    if col not in row or pd.isna(row[col]):
                        continue

                    try:
                        obs_dt = datetime(int(year), int(month), day)
                        value = float(row[col])
                    except (ValueError, TypeError):
                        continue

                    # Insert observation
                    try:
                        await session.execute(
                            text("""
                                INSERT INTO synoptic_observations
                                (station_id, obs_datetime, element, value)
                                VALUES (:station_id, :obs_datetime, :element, :value)
                            """),
                            {
                                "station_id": station_id,
                                "obs_datetime": obs_dt,
                                "element": element,
                                "value": value
                            }
                        )
                        imported += 1
                    except Exception:
                        # Duplicate or other error, skip
                        pass

            # Commit and checkpoint every group
            await session.commit()
            await session.execute(
                text("INSERT OR REPLACE INTO import_checkpoints (key, value) VALUES ('last_group', :value)"),
                {"value": group_key}
            )
            await session.commit()

            # Progress update every 100 groups
            if processed % 100 == 0:
                print(f"  Progress: {processed:,}/{total_groups:,} ({processed/total_groups*100:.1f}%) - Imported: {imported:,}")

        print(f"\n  Final Progress: {processed:,}/{total_groups:,} (100%)")

    await engine.dispose()

    print("\n" + "=" * 80)
    print("*** IMPORT COMPLETE ***")
    print("=" * 80)
    print(f"Groups processed: {processed:,}")
    print(f"Observations imported: {imported:,}")
    print(f"Groups skipped (no station): {skipped:,}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(import_observations())
