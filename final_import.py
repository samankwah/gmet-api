"""
FINAL CORRECT IMPORT SCRIPT
Maps CSV elements to actual database columns: temperature, rainfall, wind_speed, etc.
"""

import asyncio
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

CSV_PATH = "gmet_synoptic_data.csv"
DB_URL = "sqlite+aiosqlite:///gmet_weather.db"

async def final_import():
    print("="  * 80)
    print("FINAL DATA IMPORT - 2024-2025")
    print("=" * 80)

    # Load CSV
    print("\nLoading CSV...")
    df = pd.read_csv(CSV_PATH)
    df = df[(df['Year'] >= 2024) & (df['Year'] <= 2025)]
    print(f"Rows to import: {len(df):,}")

    engine = create_async_engine(DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get stations mapping
        result = await session.execute(text("SELECT id, code FROM stations"))
        stations = {code: sid for sid, code in result}
        print(f"Stations found: {len(stations)}")

        # Process by month
        grouped = df.groupby(['Station ID', 'Year', 'Month'])
        total = len(grouped)
        processed = 0
        imported = 0

        print("\nProcessing...")
        for (station_code, year, month), group in grouped:
            processed += 1

            station_id = stations.get(station_code)
            if not station_id:
                continue

            # Build observations for each day
            days_data = {}  # day -> {column: value}

            for _, row in group.iterrows():
                element = row["Element ID"]

                for day in range(1, 32):
                    col_name = str(day)
                    if col_name not in row or pd.isna(row[col_name]):
                        continue

                    try:
                        value = float(row[col_name])

                        if day not in days_data:
                            days_data[day] = {}

                        # Map element to database column
                        if element == 'Kts':
                            days_data[day]['wind_speed'] = round(value * 0.514444, 2)
                        elif element == 'RR':
                            days_data[day]['rainfall'] = value
                        elif element == 'RH':
                            days_data[day]['relative_humidity'] = int(min(100, max(0, value)))
                        elif element == 'Tx':
                            if 'temperature' in days_data[day]:
                                days_data[day]['temperature'] = (days_data[day]['temperature'] + value) / 2
                            else:
                                days_data[day]['temperature'] = value
                        elif element == 'Tn':
                            if 'temperature' in days_data[day]:
                                days_data[day]['temperature'] = (days_data[day]['temperature'] + value) / 2
                            else:
                                days_data[day]['temperature'] = value
                        elif element == 'P':
                            days_data[day]['pressure'] = value

                    except (ValueError, TypeError):
                        continue

            # Insert each day's observation
            for day, data in days_data.items():
                try:
                    obs_dt = datetime(int(year), int(month), day, 12, 0, 0, tzinfo=timezone.utc)

                    # Build dynamic INSERT with only populated columns
                    cols = ['station_id', 'obs_datetime']
                    vals = [station_id, obs_dt]

                    for col, val in data.items():
                        cols.append(col)
                        vals.append(val)

                    placeholders = ', '.join(['?' for _ in vals])
                    col_list = ', '.join(cols)

                    await session.execute(
                        text(f"INSERT OR IGNORE INTO synoptic_observations ({col_list}) VALUES ({placeholders})"),
                        vals
                    )
                    imported += 1

                except ValueError:
                    continue

            # Commit per month
            await session.commit()

            if processed % 20 == 0:
                print(f"  Progress: {processed}/{total} - Imported: {imported}")

        print(f"\nFinal: {processed}/{total} - Imported: {imported}")

    await engine.dispose()

    print("\n" + "=" * 80)
    print("IMPORT COMPLETE!")
    print("=" * 80)
    print(f"Total observations: {imported}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(final_import())
