"""
Correct import script that matches the actual database structure.
Maps CSV elements to specific columns: temperature, rainfall, wind_speed, etc.
"""

import asyncio
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

CSV_PATH = "gmet_synoptic_data.csv"
DB_URL = "sqlite+aiosqlite:///gmet_weather.db"

# Map CSV Element IDs to database columns
ELEMENT_MAP = {
    'Kts': 'wind_speed',      # Wind speed in knots -> convert to m/s
    'RR': 'rainfall',         # Rainfall in mm
    'RH': 'relative_humidity', # Relative humidity %
    'Tx': 'temperature',      # Max temperature °C
    'Tn': 'temperature',      # Min temperature °C (will average with Tx)
    'P': 'pressure',          # Pressure in hPa
}

async def correct_import():
    print("=" * 80)
    print("IMPORTING WEATHER DATA - 2024-2025")
    print("=" * 80)

    # Load and filter CSV
    print(f"\nLoading CSV...")
    df = pd.read_csv(CSV_PATH)
    print(f"Total rows: {len(df):,}")

    # Filter for 2024-2025
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

        # Group by station, year, month to build complete observations
        print("\nProcessing observations...")
        grouped = df.groupby(['Station ID', 'Year', 'Month'])

        total_groups = len(grouped)
        processed = 0
        imported = 0

        for (station_code, year, month), group in grouped:
            processed += 1

            station_id = stations.get(station_code)
            if not station_id:
                continue

            # Build observations for each day of the month
            obs_dict = {}  # key: day, value: {column: value}

            for _, row in group.iterrows():
                element = row["Element ID"]

                if element not in ELEMENT_MAP:
                    continue

                db_column = ELEMENT_MAP[element]

                # Process each day
                for day in range(1, 32):
                    col = str(day)
                    if col not in row or pd.isna(row[col]):
                        continue

                    try:
                        value = float(row[col])

                        # Convert units if needed
                        if element == 'Kts':
                            value = round(value * 0.514444, 2)  # knots to m/s
                        elif element == 'RH':
                            value = int(value)  # humidity as integer

                        # Initialize day if needed
                        if day not in obs_dict:
                            obs_dict[day] = {}

                        # Handle temperature (average Tx and Tn if both exist)
                        if db_column == 'temperature':
                            if db_column in obs_dict[day]:
                                obs_dict[day][db_column] = (obs_dict[day][db_column] + value) / 2
                            else:
                                obs_dict[day][db_column] = value
                        else:
                            obs_dict[day][db_column] = value

                    except (ValueError, TypeError):
                        continue

            # Insert observations for this month
            for day, data in obs_dict.items():
                try:
                    obs_dt = datetime(int(year), int(month), day, 12, 0, 0, tzinfo=timezone.utc)

                    # Build INSERT statement with only non-null columns
                    columns = ['station_id', 'obs_datetime'] + list(data.keys())
                    placeholders = ', '.join(['?' for _ in columns])
                    column_names = ', '.join(columns)

                    values = [station_id, obs_dt] + list(data.values())

                    await session.execute(
                        text(f"""
                            INSERT OR IGNORE INTO synoptic_observations
                            ({column_names})
                            VALUES ({placeholders})
                        """),
                        values
                    )
                    imported += 1

                except ValueError:
                    continue  # Invalid date

            # Commit after each month
            await session.commit()

            if processed % 10 == 0:
                print(f"  Progress: {processed}/{total_groups} groups - {imported:,} observations imported")

        print(f"\n  Final: {processed}/{total_groups} groups - {imported:,} observations imported")

    await engine.dispose()

    print("\n" + "=" * 80)
    print("*** IMPORT COMPLETE ***")
    print("=" * 80)
    print(f"Observations imported: {imported:,}")
    print("=" * 80)
    print("\nTest the API now!")
    print("Run: python check_db_data.py")

if __name__ == "__main__":
    asyncio.run(correct_import())
