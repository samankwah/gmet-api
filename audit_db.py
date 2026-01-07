import sys
import os
import asyncio
import pandas as pd
from sqlalchemy import select, func, extract
from datetime import datetime, timedelta

# -----------------------------
# Add project root to Python path
# -----------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# -----------------------------
# Imports
# -----------------------------
try:
    from app.db import async_session
from app.models.weather_data import Station, SynopticObservation
except ModuleNotFoundError:
    print("ERROR: Cannot find app.db. Make sure your folder structure is correct:")
    print("met-api/")
    print("  audit_db.py")
    print("  app/")
    print("    __init__.py")
    print("    db.py")
    print("    models/")
    print("      __init__.py")
    print("      weather_data.py")
    raise

# -----------------------------
# Utility Functions
# -----------------------------
async def get_stations(session):
    result = await session.execute(select(Station))
    return result.scalars().all()

async def get_observations(session, station_id):
    result = await session.execute(
        select(SynopticObservation)
        .where(SynopticObservation.station_id == station_id)
        .order_by(SynopticObservation.obs_datetime)
    )
    return result.scalars().all()

def expected_days(year):
    """Return number of days in the year."""
    start = datetime(year, 1, 1)
    end = datetime(year, 12, 31)
    return (end - start).days + 1

# -----------------------------
# Main Audit Function
# -----------------------------
async def audit_db():
    async with async_session() as session:
        print("\n===== GMET DATABASE AUDIT =====\n")

        # Total stations
        station_count = (await session.execute(select(func.count(Station.id)))).scalar()
        print(f"Total stations: {station_count}")

        # Total observations
        obs_count = (await session.execute(select(func.count(SynopticObservation.id)))).scalar()
        print(f"Total observations: {obs_count}\n")

        # Observations per station
        print("Observations per station:")
        result = await session.execute(
            select(Station.name, func.count(SynopticObservation.id))
            .join(SynopticObservation)
            .group_by(Station.id)
            .order_by(Station.name)
        )
        obs_per_station = []
        for name, count in result:
            obs_per_station.append((name, count))
            print(f"  {name}: {count}")

        # Last 5 observations for each station
        print("\nLast 5 observations per station:")
        for station_name, _ in obs_per_station:
            res = await session.execute(
                select(SynopticObservation)
                .join(Station)
                .where(Station.name == station_name)
                .order_by(SynopticObservation.obs_datetime.desc())
                .limit(5)
            )
            print(f"\nStation: {station_name}")
            for obs in res.scalars():
                print(f"  {obs.obs_datetime} | Temp: {obs.temperature}°C | Rainfall: {obs.rainfall}mm | Wind: {obs.wind_speed}m/s")

        # Missing dates and completeness per year
        print("\nChecking missing observations and completeness per year...\n")
        audit_records = []

        for station in await get_stations(session):
            obs_list = await get_observations(session, station.id)
            obs_dates = set([obs.obs_datetime.date() for obs in obs_list])
            if not obs_dates:
                continue

            years = set([d.year for d in obs_dates])
            for year in sorted(years):
                start_date = datetime(year, 1, 1).date()
                end_date = datetime(year, 12, 31).date()
                expected = set([start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)])
                missing = sorted(list(expected - obs_dates))
                completeness = round((1 - len(missing)/len(expected))*100, 2)
                
                audit_records.append({
                    "station": station.name,
                    "year": year,
                    "total_expected_days": len(expected),
                    "observed_days": len(obs_dates & expected),
                    "missing_days": len(missing),
                    "completeness_%": completeness
                })

        df_audit = pd.DataFrame(audit_records)
        print(df_audit.head(10))

        # Export CSV
        audit_csv = os.path.join(PROJECT_ROOT, "gmet_audit_report.csv")
        df_audit.to_csv(audit_csv, index=False)
        print(f"\n✅ Audit report exported: {audit_csv}\n")

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    asyncio.run(audit_db())



# import sys
# import os
# import asyncio
# from sqlalchemy import select, func

# # Make sure Python can see your package
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# from app.db import async_session
# from app.models.weather_data import Station, SynopticObservation


# async def audit_db():
#     async with async_session() as session:
#         # Count all stations
#         station_count_result = await session.execute(select(func.count(Station.id)))
#         station_count = station_count_result.scalar()
#         print(f"Total stations: {station_count}")

#         # Count all observations
#         obs_count_result = await session.execute(select(func.count(SynopticObservation.id)))
#         obs_count = obs_count_result.scalar()
#         print(f"Total observations: {obs_count}")

#         # Last 5 observations for Tema
#         result = await session.execute(
#             select(SynopticObservation)
#             .join(Station)
#             .where(Station.name == "Tema")
#             .order_by(SynopticObservation.obs_datetime.desc())
#             .limit(5)
#         )
#         print("\nLast 5 observations for Tema:")
#         for obs in result.scalars():
#             print(f"{obs.obs_datetime} | Temp: {obs.temperature}°C | Rainfall: {obs.rainfall}mm | Wind: {obs.wind_speed}m/s")


# if __name__ == "__main__":
#     asyncio.run(audit_db())
