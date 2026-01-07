"""
Quick database audit script to check what data exists in gmet_weather.db

This script helps verify:
- Number of stations in the database
- Number of observations in the database
- List of available stations with codes
- Sample observation data
- Date ranges of available data
"""

import asyncio
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Database configuration
DB_URL = "sqlite+aiosqlite:///gmet_weather.db"

async def check_database():
    """Check the database and display current status."""
    print("=" * 80)
    print("GMet Weather Database Audit")
    print("=" * 80)
    print(f"Database: {DB_URL}")
    print()

    engine = create_async_engine(DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Check if tables exist
            try:
                # Count stations
                result = await session.execute(text("SELECT COUNT(*) FROM stations"))
                station_count = result.scalar()
                print(f"Stations in database: {station_count:,}")

                # Count observations
                result = await session.execute(text("SELECT COUNT(*) FROM synoptic_observations"))
                obs_count = result.scalar()
                print(f"Observations in database: {obs_count:,}")
                print()

                if station_count > 0:
                    print("-" * 80)
                    print("Available Stations:")
                    print("-" * 80)

                    # List all stations
                    result = await session.execute(
                        text("""
                            SELECT code, name, latitude, longitude
                            FROM stations
                            ORDER BY name
                        """)
                    )
                    stations = result.fetchall()

                    for i, (code, name, lat, lon) in enumerate(stations, 1):
                        lat_str = f"{lat:.4f}" if lat else "N/A"
                        lon_str = f"{lon:.4f}" if lon else "N/A"
                        print(f"  {i:2d}. {name:20s} (Code: {code:12s}) Lat: {lat_str:10s} Lon: {lon_str:10s}")
                    print()

                if obs_count > 0:
                    print("-" * 80)
                    print("Observation Data Summary:")
                    print("-" * 80)

                    # Get date range
                    result = await session.execute(
                        text("""
                            SELECT
                                MIN(obs_datetime) as earliest,
                                MAX(obs_datetime) as latest
                            FROM synoptic_observations
                        """)
                    )
                    earliest, latest = result.fetchone()
                    print(f"  Date range: {earliest} to {latest}")

                    # Get element counts
                    result = await session.execute(
                        text("""
                            SELECT element, COUNT(*) as count
                            FROM synoptic_observations
                            GROUP BY element
                            ORDER BY count DESC
                        """)
                    )
                    elements = result.fetchall()
                    print(f"\n  Data by element:")
                    for element, count in elements:
                        print(f"    {element:10s}: {count:,} observations")

                    # Show sample observations
                    print(f"\n  Sample observations (latest 5):")
                    result = await session.execute(
                        text("""
                            SELECT s.name, so.obs_datetime, so.element, so.value
                            FROM synoptic_observations so
                            JOIN stations s ON s.id = so.station_id
                            ORDER BY so.obs_datetime DESC
                            LIMIT 5
                        """)
                    )
                    samples = result.fetchall()
                    for station, datetime, element, value in samples:
                        print(f"    {station:15s} | {datetime} | {element:6s} = {value}")
                    print()

                if station_count == 0 and obs_count == 0:
                    print("=" * 80)
                    print("DATABASE IS EMPTY")
                    print("=" * 80)
                    print("Run 'python import_gmet_data.py' to import data from CSV")
                    print()

            except Exception as e:
                print(f"Error querying database: {e}")
                print("Database may not be initialized yet.")
                print()

    finally:
        await engine.dispose()

    print("=" * 80)
    print("Audit Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(check_database())
