"""
Import weather data from Excel file into the database.

This script imports station information and weather observations from
the Excel file 'Rdata_ALL List 1.xlsx' into the database.
"""

import pandas as pd
import asyncio
from datetime import datetime, time
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, engine
from app.models.station import Station
from app.models.synoptic_observation import SynopticObservation
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionClass

# File path
EXCEL_FILE = r"C:\Users\CRAFT\OneDrive - Smart Workplace\Documents\dataset\Excel\Rdata_ALL List 1.xlsx"

# Element ID mapping to database fields
ELEMENT_MAPPING = {
    'Tx': 'temperature_max',  # Maximum temperature
    'Tn': 'temperature_min',  # Minimum temperature
    'Kts': 'wind_speed',      # Wind speed in knots
    'RH': 'relative_humidity', # Relative humidity
    'P': 'pressure',          # Pressure
    'RR': 'precipitation',    # Rainfall/Precipitation
}


async def import_stations(df: pd.DataFrame, session: AsyncSessionClass):
    """Import unique stations from the dataframe."""
    print("\n" + "="*60)
    print("IMPORTING STATIONS")
    print("="*60)
    
    # Get unique stations
    stations_df = df[['Station ID', 'Name', 'Geogr1', 'Geogr2']].drop_duplicates()
    
    imported = 0
    skipped = 0
    
    for _, row in stations_df.iterrows():
        station_id = str(row['Station ID']).strip()
        
        # Check if station exists
        result = await session.execute(
            select(Station).where(Station.station_id == station_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            skipped += 1
            continue
        
        # Create new station
        station = Station(
            station_id=station_id,
            name=str(row['Name']).strip(),
            latitude=float(row['Geogr2']),
            longitude=float(row['Geogr1']),
            elevation=None,  # Not provided in Excel
            is_active=True
        )
        
        session.add(station)
        imported += 1
        
        if imported % 10 == 0:
            print(f"  Imported {imported} stations...")
    
    await session.commit()
    
    print(f"\n✓ Stations imported: {imported}")
    print(f"  Stations skipped (already exist): {skipped}")
    
    return imported, skipped


async def import_observations(df: pd.DataFrame, session: AsyncSessionClass):
    """Import weather observations from the dataframe."""
    print("\n" + "="*60)
    print("IMPORTING OBSERVATIONS")
    print("="*60)
    
    imported = 0
    skipped = 0
    errors = 0
    
    total_rows = len(df)
    
    for idx, row in df.iterrows():
        if idx % 100 == 0:
            print(f"  Processing row {idx}/{total_rows}...")
        
        try:
            station_id = str(row['Station ID']).strip()
            element_id = str(row['Element ID']).strip()
            year = int(row['Year'])
            month = int(row['Month'])
            
            # Parse observation time
            if isinstance(row['Time'], str):
                obs_time = datetime.strptime(row['Time'], '%H:%M:%S').time()
            else:
                obs_time = time(9, 0, 0)  # Default to 09:00:00
            
            # Check if element is mapped
            if element_id not in ELEMENT_MAPPING:
                print(f"  Warning: Unknown element ID '{element_id}' - skipping")
                skipped += 1
                continue
            
            field_name = ELEMENT_MAPPING[element_id]
            
            # Process each day of the month
            for day in range(1, 32):  # Days 1-31
                if day not in row.index:
                    continue
                
                value = row[day]
                
                # Skip NaN or empty values
                if pd.isna(value) or value == '':
                    continue
                
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    continue
                
                # Create observation datetime
                try:
                    obs_datetime = datetime(year, month, day, 
                                          obs_time.hour, obs_time.minute, obs_time.second)
                except ValueError:
                    # Invalid date (e.g., Feb 31)
                    continue
                
                # Check if observation already exists
                result = await session.execute(
                    select(SynopticObservation).where(
                        SynopticObservation.station_id == station_id,
                        SynopticObservation.observation_time == obs_datetime
                    )
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing observation
                    setattr(existing, field_name, value)
                else:
                    # Create new observation
                    obs_data = {
                        'station_id': station_id,
                        'observation_time': obs_datetime,
                        field_name: value
                    }
                    obs = SynopticObservation(**obs_data)
                    session.add(obs)
                    imported += 1
                
                # Commit every 500 records to avoid memory issues
                if imported % 500 == 0:
                    await session.commit()
        
        except Exception as e:
            errors += 1
            print(f"  Error processing row {idx}: {e}")
            continue
    
    # Final commit
    await session.commit()
    
    print(f"\n✓ Observations imported: {imported}")
    print(f"  Observations skipped: {skipped}")
    print(f"  Errors: {errors}")
    
    return imported, skipped, errors


async def main():
    """Main import function."""
    print("\n" + "="*60)
    print("WEATHER DATA IMPORT FROM EXCEL")
    print("="*60)
    print(f"File: {EXCEL_FILE}")
    
    # Check if file exists
    if not Path(EXCEL_FILE).exists():
        print(f"\n❌ Error: File not found: {EXCEL_FILE}")
        return
    
    # Read Excel file
    print("\nReading Excel file...")
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name='Rdata_ALL List 1')
        print(f"✓ Loaded {len(df)} rows from Excel")
        print(f"  Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"\n❌ Error reading Excel file: {e}")
        return
    
    # Create database session
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Import stations first
        stations_imported, stations_skipped = await import_stations(df, session)
        
        # Import observations
        obs_imported, obs_skipped, obs_errors = await import_observations(df, session)
    
    # Summary
    print("\n" + "="*60)
    print("IMPORT SUMMARY")
    print("="*60)
    print(f"Stations imported: {stations_imported}")
    print(f"Stations skipped: {stations_skipped}")
    print(f"Observations imported: {obs_imported}")
    print(f"Observations skipped: {obs_skipped}")
    print(f"Errors: {obs_errors}")
    print("\n✓ Import completed!")


if __name__ == "__main__":
    asyncio.run(main())