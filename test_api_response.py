"""
Test script to verify API responses work correctly.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.crud.weather import observation as observation_crud, station as station_crud
from app.schemas.weather import ObservationResponse

DB_URL = "sqlite+aiosqlite:///gmet_weather.db"

async def test_api_response():
    print("=" * 80)
    print("Testing API Response Serialization")
    print("=" * 80)

    engine = create_async_engine(DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Test 1: Get a station by name
        print("\n1. Testing station lookup by name...")
        all_stations = await station_crud.get_multi(db, skip=0, limit=1000)
        tema_station = None
        for s in all_stations:
            if "Tema" in s.name:
                tema_station = s
                print(f"   Found: {s.name} (Code: {s.code}, ID: {s.id})")
                break

        if not tema_station:
            print("   ERROR: Tema station not found!")
            return

        # Test 2: Get latest observation for Tema
        print("\n2. Testing get_latest_for_station...")
        observation = await observation_crud.get_latest_for_station(db, station_id=tema_station.id)

        if not observation:
            print("   ERROR: No observations found for Tema!")
            return

        print(f"   Found observation ID: {observation.id}")
        print(f"   Station ID: {observation.station_id}")
        print(f"   Datetime: {observation.obs_datetime}")
        print(f"   Temperature: {observation.temperature}°C")
        print(f"   Rainfall: {observation.rainfall}mm")
        print(f"   Wind Speed: {observation.wind_speed}m/s")
        print(f"   Relative Humidity: {observation.relative_humidity}%")

        # Test 3: Serialize to Pydantic schema
        print("\n3. Testing Pydantic serialization...")
        try:
            response = ObservationResponse.model_validate(observation)
            print("   SUCCESS! Serialized to ObservationResponse")
            print(f"   Response obs_datetime: {response.obs_datetime}")
            print(f"   Response temperature: {response.temperature}°C")
            print(f"   Response relative_humidity: {response.relative_humidity}%")

            # Convert to JSON dict
            response_dict = response.model_dump()
            print("\n4. JSON representation:")
            import json
            print(json.dumps(response_dict, indent=2, default=str))

        except Exception as e:
            print(f"   ERROR: Failed to serialize: {e}")
            import traceback
            traceback.print_exc()

    await engine.dispose()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_api_response())
