"""
Quick import of sample observations for testing the API.
Imports just 2024-2025 data for faster testing.
"""

import asyncio
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

CSV_PATH = "gmet_synoptic_data.csv"
DB_URL = "sqlite+aiosqlite:///gmet_weather.db"

async def quick_import():
    print("=" * 80)
    print("QUICK IMPORT - 2024-2025 DATA ONLY")
    print("=" * 80)

    # Load CSV
    print(f"\nLoading CSV...")
    df = pd.read_csv(CSV_PATH)
    print(f"Total rows: {len(df):,}")

    # Filter for recent years only
    df = df[(df['Year'] >= 2024) & (df['Year'] <= 2025)]
    print(f"Filtered to 2024-2025: {len(df):,} rows")

    engine = create_async_engine(DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get stations
        print("\nFetching stations...")
        result = await session.execute(text("SELECT id, code FROM stations"))
        stations = {code: station_id for station_id, code in result}
        print(f"Found {len(stations)} stations")

        imported = 0
        skipped = 0

        print("\nImporting observations...")
        for idx, row in df.iterrows():
            station_code = row["Station ID"]
            station_id = stations.get(station_code)

            if not station_id:
                skipped += 1
                continue

            element = row["Element ID"]
            year = int(row["Year"])
            month = int(row["Month"])

            # Process each day
            for day in range(1, 32):
                col = str(day)
                if col not in row or pd.isna(row[col]):
                    continue

                try:
                    obs_dt = datetime(year, month, day)
                    value = float(row[col])

                    # Insert
                    await session.execute(
                        text("""
                            INSERT OR IGNORE INTO synoptic_observations
                            (station_id, obs_datetime, element, value)
                            VALUES (:sid, :dt, :elem, :val)
                        """),
                        {"sid": station_id, "dt": obs_dt, "elem": element, "val": value}
                    )
                    imported += 1

                except (ValueError, TypeError):
                    continue

            # Commit every 100 rows
            if idx % 100 == 0:
                await session.commit()
                print(f"  Processed {idx:,}/{len(df):,} rows... Imported {imported:,} observations")

        # Final commit
        await session.commit()

    await engine.dispose()

    print("\n" * 80)
    print("*** IMPORT COMPLETE ***")
    print("=" * 80)
    print(f"Observations imported: {imported:,}")
    print(f"Rows skipped: {skipped:,}")
    print("=" * 80)
    print("\nYou can now test the API with 2024-2025 data!")
    print("Run: python check_db_data.py")

if __name__ == "__main__":
    asyncio.run(quick_import())
