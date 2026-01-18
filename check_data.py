"""Check if there are stations and observations in the database."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB = "postgresql+asyncpg://gmet_weather_6nsz_user:JVLHyY3wOV4k45yH7cxwMEoyfRhhOUlD@dpg-d5feauje5dus73bemddg-a/gmet_weather_6nsz"

async def check():
    engine = create_async_engine(DB)
    async with engine.connect() as conn:
        # Check stations
        result = await conn.execute(text("SELECT COUNT(*) FROM stations"))
        station_count = result.scalar()
        print(f"Stations: {station_count}")

        if station_count > 0:
            result = await conn.execute(text("SELECT id, code, name FROM stations LIMIT 5"))
            rows = result.fetchall()
            print("\nFirst 5 stations:")
            for row in rows:
                print(f"  ID={row[0]}, Code={row[1]}, Name={row[2]}")

        # Check observations
        result = await conn.execute(text("SELECT COUNT(*) FROM observations"))
        obs_count = result.scalar()
        print(f"\nObservations: {obs_count}")

        # Check daily_summaries
        result = await conn.execute(text("SELECT COUNT(*) FROM daily_summaries"))
        daily_count = result.scalar()
        print(f"Daily summaries: {daily_count}")

        if daily_count > 0:
            result = await conn.execute(text(
                "SELECT station_id, date, temp_min, temp_max FROM daily_summaries ORDER BY date DESC LIMIT 3"
            ))
            rows = result.fetchall()
            print("\nLatest 3 daily summaries:")
            for row in rows:
                print(f"  Station={row[0]}, Date={row[1]}, Min={row[2]}, Max={row[3]}")

asyncio.run(check())
