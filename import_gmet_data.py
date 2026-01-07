# """
# Import GMet historical synoptic data from CSV.
# Handles data from 1960-2024 with multiple stations and climate parameters.

# CSV Structure:
# Station ID, Lon, Lat, Name, Element ID, Year, Month, Time, Data Type, 1-31 (daily values)

# Climate Parameters:
# - Kts: Wind speed in knots
# - Rh: Relative Humidity (%)
# - RR: Rainfall (mm)
# - SUNHR: Sunshine hours
# - Tx: Maximum temperature (°C)
# - Tn: Minimum temperature (°C)
# """
# import asyncio
# import pandas as pd
# import numpy as np
# from datetime import datetime, timezone
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.future import select
# from typing import Dict, Set

# from app.config import settings
# from app.models.weather_data import Station, SynopticObservation


# # Map Ghana regions (you can update these based on actual station locations)
# STATION_REGIONS = {
#     "Tema": "Greater Accra",
#     "Accra": "Greater Accra",
#     "Kumasi": "Ashanti",
#     "Tamale": "Northern",
#     "Takoradi": "Western",
#     "Cape Coast": "Central",
#     "Sunyani": "Bono",
#     "Ho": "Volta",
#     "Koforidua": "Eastern",
#     "Wa": "Upper West",
#     "Bolgatanga": "Upper East",
#     # Add more stations as needed
# }


# async def import_gmet_synoptic_data(csv_file_path: str, batch_size: int = 1000):
#     """
#     Import GMet synoptic data from CSV file.
    
#     Args:
#         csv_file_path: Path to the CSV file
#         batch_size: Number of observations to commit at once
#     """
#     print("=" * 80)
#     print("GMet Historical Synoptic Data Import Tool (1960-2024)")
#     print("=" * 80)
    
#     # Load CSV
#     print(f"\n📂 Loading CSV file: {csv_file_path}")
#     try:
#         df = pd.read_csv(csv_file_path)
#         print(f"✅ Loaded {len(df):,} rows")
#     except Exception as e:
#         print(f"❌ Error loading CSV: {e}")
#         return
    
#     # Display structure
#     print(f"\n📋 Columns found: {list(df.columns)}")
#     print(f"📊 Unique stations: {df['Station ID'].nunique()}")
#     print(f"📊 Unique elements: {df['Element ID'].unique()}")
#     print(f"📊 Year range: {df['Year'].min()} - {df['Year'].max()}")
    
#     # Connect to database
#     engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
#     async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
#     async with async_session() as session:
#         # Step 1: Import/Update Stations
#         print("\n" + "=" * 80)
#         print("STEP 1: Importing Stations")
#         print("=" * 80)
        
#         stations_data = df[['Station ID', 'Name', 'Lon', 'Lat']].drop_duplicates()
#         station_map = {}  # Maps Station ID to database ID
        
#         for _, row in stations_data.iterrows():
#             station_code = str(row['Station ID']).strip().upper()
#             station_name = str(row['Name']).strip()
#             lon = float(row['Lon']) if pd.notna(row['Lon']) else None
#             lat = float(row['Lat']) if pd.notna(row['Lat']) else None
            
#             # Determine region
#             region = STATION_REGIONS.get(station_name, "Unknown")
            
#             # Check if station exists
#             result = await session.execute(
#                 select(Station).where(Station.code == station_code)
#             )
#             station = result.scalar_one_or_none()
            
#             if not station:
#                 station = Station(
#                     name=station_name,
#                     code=station_code,
#                     latitude=lat,
#                     longitude=lon,
#                     region=region
#                 )
#                 session.add(station)
#                 await session.flush()
#                 print(f"  ✅ Created: {station_name} ({station_code}) - {region}")
#             else:
#                 # Update coordinates if they were missing
#                 if not station.latitude and lat:
#                     station.latitude = lat
#                 if not station.longitude and lon:
#                     station.longitude = lon
#                 if station.region == "Unknown" and region != "Unknown":
#                     station.region = region
#                 print(f"  ℹ️  Exists: {station_name} ({station_code})")
            
#             station_map[row['Station ID']] = station.id
        
#         await session.commit()
#         print(f"\n✅ Processed {len(station_map)} stations")
        
#         # Step 2: Import Observations
#         print("\n" + "=" * 80)
#         print("STEP 2: Importing Observations")
#         print("=" * 80)
#         print("This may take several minutes for 60+ years of data...")
        
#         # Process by station, year, month for efficiency
#         observations_to_add = []
#         observations_added = 0
#         observations_skipped = 0
#         errors = 0
        
#         # Get existing observations to avoid duplicates
#         print("\n🔍 Checking for existing observations...")
#         result = await session.execute(
#             select(
#                 SynopticObservation.station_id,
#                 SynopticObservation.obs_datetime
#             )
#         )
#         existing_obs: Set[tuple] = {
#             (row.station_id, row.obs_datetime) 
#             for row in result
#         }
#         print(f"  Found {len(existing_obs):,} existing observations")
        
#         # Group by station, year, month, element for processing
#         grouped = df.groupby(['Station ID', 'Year', 'Month'])
#         total_groups = len(grouped)
#         processed = 0
        
#         print(f"\n📦 Processing {total_groups:,} station-month combinations...")
        
#         # Dictionary to collect all parameters for each observation
#         obs_dict: Dict[tuple, dict] = {}
        
#         for (station_id, year, month), month_data in grouped:
#             processed += 1
            
#             if processed % 50 == 0 or processed == total_groups:
#                 print(f"  Progress: {processed:,}/{total_groups:,} ({processed/total_groups*100:.1f}%)")
            
#             station_db_id = station_map.get(station_id)
#             if not station_db_id:
#                 continue
            
#             # Process each day (columns 1-31)
#             for day in range(1, 32):
#                 day_col = str(day)
#                 if day_col not in df.columns:
#                     continue
                
#                 # Validate date
#                 try:
#                     obs_date = datetime(int(year), int(month), day, 12, 0, 0, tzinfo=timezone.utc)
#                 except ValueError:
#                     continue  # Invalid date (e.g., Feb 30)
                
#                 obs_key = (station_db_id, obs_date)
                
#                 # Skip if already exists in database
#                 if obs_key in existing_obs:
#                     observations_skipped += 1
#                     continue
                
#                 # Initialize observation data if not exists
#                 if obs_key not in obs_dict:
#                     obs_dict[obs_key] = {
#                         'station_id': station_db_id,
#                         'obs_datetime': obs_date,
#                         'temperature': None,
#                         'relative_humidity': None,
#                         'wind_speed': None,
#                         'rainfall': None,
#                         'pressure': None
#                     }
                
#                 # Process each element (parameter) for this day
#                 for _, row in month_data.iterrows():
#                     element_id = str(row['Element ID']).strip().upper()
#                     value = row.get(day_col)
                    
#                     # Skip missing or invalid values
#                     if pd.isna(value) or value == '' or value in [-999, -9999, 'NaN']:
#                         continue
                    
#                     try:
#                         value = float(value)
                        
#                         # Map element to observation field
#                         if element_id == 'TX':  # Max temperature
#                             if obs_dict[obs_key]['temperature'] is None:
#                                 obs_dict[obs_key]['temperature'] = value
#                             else:
#                                 # Average Tx and Tn if both exist
#                                 obs_dict[obs_key]['temperature'] = (obs_dict[obs_key]['temperature'] + value) / 2
                        
#                         elif element_id == 'TN':  # Min temperature
#                             if obs_dict[obs_key]['temperature'] is None:
#                                 obs_dict[obs_key]['temperature'] = value
#                             else:
#                                 # Average Tx and Tn
#                                 obs_dict[obs_key]['temperature'] = (obs_dict[obs_key]['temperature'] + value) / 2
                        
#                         elif element_id == 'RR':  # Rainfall
#                             obs_dict[obs_key]['rainfall'] = value
                        
#                         elif element_id == 'RH':  # Relative Humidity
#                             obs_dict[obs_key]['relative_humidity'] = int(value) if 0 <= value <= 100 else None
                        
#                         elif element_id == 'KTS':  # Wind speed in knots
#                             # Convert knots to m/s (1 knot = 0.514444 m/s)
#                             obs_dict[obs_key]['wind_speed'] = round(value * 0.514444, 2)
                        
#                         # Note: SUNHR and pressure not in current schema
#                         # Add to model if needed
                        
#                     except (ValueError, TypeError) as e:
#                         errors += 1
#                         continue
        
#         # Convert dictionary to list of observations
#         print(f"\n💾 Preparing {len(obs_dict):,} observations for import...")
        
#         for obs_key, obs_data in obs_dict.items():
#             # Only add if at least one parameter has data
#             if any(v is not None for k, v in obs_data.items() 
#                    if k not in ['station_id', 'obs_datetime']):
#                 observations_to_add.append(SynopticObservation(**obs_data))
#                 observations_added += 1
                
#                 # Commit in batches
#                 if len(observations_to_add) >= batch_size:
#                     session.add_all(observations_to_add)
#                     await session.commit()
#                     print(f"  💾 Committed batch: {observations_added:,} total observations")
#                     observations_to_add = []
        
#         # Commit remaining observations
#         if observations_to_add:
#             session.add_all(observations_to_add)
#             await session.commit()
#             print(f"  💾 Committed final batch")
        
#         # Final summary
#         print("\n" + "=" * 80)
#         print("✅ IMPORT COMPLETE!")
#         print("=" * 80)
#         print(f"📊 Statistics:")
#         print(f"  • Stations processed: {len(station_map)}")
#         print(f"  • Observations added: {observations_added:,}")
#         print(f"  • Observations skipped (existing): {observations_skipped:,}")
#         print(f"  • Errors encountered: {errors:,}")
#         print(f"  • Total data points processed: {len(df) * 31:,}")
#         print("=" * 80)
#         print("\n🎉 Your GMet API is now loaded with historical data!")
#         print("\nTest it with:")
#         print("  curl -X GET 'http://127.0.0.1:8000/v1/current?location=Tema' \\")
#         print("    -H 'X-API-Key: e4oV7CpCNlIgpq4HZ1Tlk1z2dl5Cf7RT'")
#         print("=" * 80)
    
#     await engine.dispose()


# if __name__ == "__main__":
#     csv_path = r"C:\Users\CRAFT\Desktop\future MEST projects\Backend\met-api\docs\synoptic dataset_1960 -2024.csv"
#     asyncio.run(import_gmet_synoptic_data(csv_path))



import asyncio
import pandas as pd
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# =============================================================================
# CONFIG
# =============================================================================

CSV_PATH = "gmet_synoptic_data.csv"   # <-- update if needed
DB_URL = "sqlite+aiosqlite:///gmet_weather.db"

Base = declarative_base()

engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# =============================================================================
# MODELS
# =============================================================================

class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    observations = relationship("SynopticObservation", back_populates="station")


class SynopticObservation(Base):
    __tablename__ = "synoptic_observations"

    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey("stations.id"))
    obs_datetime = Column(DateTime, index=True)
    element = Column(String)
    value = Column(Float)

    station = relationship("Station", back_populates="observations")

    __table_args__ = (
        UniqueConstraint(
            "station_id", "obs_datetime", "element",
            name="uq_station_datetime_element"
        ),
    )


class ImportCheckpoint(Base):
    __tablename__ = "import_checkpoints"

    key = Column(String, primary_key=True)
    value = Column(String)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

# =============================================================================
# DB INIT
# =============================================================================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# =============================================================================
# CHECKPOINT HELPERS
# =============================================================================

async def get_checkpoint(session: AsyncSession, key: str):
    result = await session.execute(
        select(ImportCheckpoint.value).where(ImportCheckpoint.key == key)
    )
    return result.scalar_one_or_none()


async def set_checkpoint(session: AsyncSession, key: str, value: str):
    cp = await session.get(ImportCheckpoint, key)
    if cp:
        cp.value = value
    else:
        session.add(ImportCheckpoint(key=key, value=value))
    await session.commit()

# =============================================================================
# AUDIT
# =============================================================================

def audit_csv(df: pd.DataFrame):
    report = {
        "Missing coordinates": int(
            df["Lat"].isna().sum() + df["Lon"].isna().sum()
        ),
        "Duplicate station IDs": int(df["Station ID"].duplicated().sum()),
    }
    print("\n*** CSV AUDIT REPORT ***")
    for k, v in report.items():
        print(f"  {k}: {v}")

# =============================================================================
# IMPORT LOGIC
# =============================================================================

async def import_gmet_synoptic_data(csv_path: str):
    print("=" * 80)
    print("GMET HISTORICAL SYNOPTIC DATA IMPORT")
    print("=" * 80)

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows")

    audit_csv(df)

    async with AsyncSessionLocal() as session:

        # ---------------------------------------------------------------------
        # STEP 1: STATIONS
        # ---------------------------------------------------------------------
        print("\nSTEP 1: STATIONS")

        stations = {}
        for _, row in df.iterrows():
            code = row["Station ID"]
            if code in stations:
                continue

            result = await session.execute(
                select(Station).where(Station.code == code)
            )
            station = result.scalar_one_or_none()

            if not station:
                lat = row["Lat"] if pd.notna(row["Lat"]) else None
                lon = row["Lon"] if pd.notna(row["Lon"]) else None
                station = Station(
                    code=code,
                    name=row["Name"],
                    latitude=lat,
                    longitude=lon,
                )
                session.add(station)
                await session.flush()

            stations[code] = station

        await session.commit()
        print(f"✅ Stations processed: {len(stations)}")

        # ---------------------------------------------------------------------
        # STEP 2: OBSERVATIONS (MONTHLY CHECKPOINTED)
        # ---------------------------------------------------------------------
        print("\nSTEP 2: OBSERVATIONS")

        last_group = await get_checkpoint(session, "last_group")

        grouped = df.groupby(["Station ID", "Year", "Month"])

        for (station_code, year, month), group in grouped:
            group_key = f"{station_code}-{year}-{month}"

            if last_group and group_key <= last_group:
                continue

            station = stations.get(station_code)
            if not station:
                continue

            for _, row in group.iterrows():
                element = row["Element ID"]

                for day in range(1, 32):
                    col = str(day)
                    if col not in row or pd.isna(row[col]):
                        continue

                    try:
                        obs_dt = datetime(int(year), int(month), day)
                    except ValueError:
                        continue

                    obs = SynopticObservation(
                        station_id=station.id,
                        obs_datetime=obs_dt,
                        element=element,
                        value=float(row[col]),
                    )

                    session.add(obs)

            await session.commit()
            await set_checkpoint(session, "last_group", group_key)
            print(f"  ✔ Imported {group_key}")

    print("\n*** IMPORT COMPLETE ***")

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    asyncio.run(init_db())
    asyncio.run(import_gmet_synoptic_data(CSV_PATH))
