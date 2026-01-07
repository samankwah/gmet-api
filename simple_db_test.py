"""
Simple database test to verify observation data.
"""
import asyncio
import aiosqlite
import json

async def test():
    print("=" * 80)
    print("Testing Database Query for API")
    print("=" * 80)

    async with aiosqlite.connect('gmet_weather.db') as db:
        # Test 1: Find Tema station
        print("\n1. Finding Tema station...")
        async with db.execute("SELECT id, name, code FROM stations WHERE name LIKE '%Tema%'") as cursor:
            async for station_id, name, code in cursor:
                print(f"   Found: {name} (Code: {code}, ID: {station_id})")

                # Test 2: Get latest observation for this station
                print(f"\n2. Getting latest observation for station ID {station_id}...")
                async with db.execute("""
                    SELECT id, station_id, obs_datetime, temperature, rainfall,
                           wind_speed, relative_humidity, wind_direction, pressure
                    FROM synoptic_observations
                    WHERE station_id = ?
                    ORDER BY obs_datetime DESC
                    LIMIT 1
                """, (station_id,)) as obs_cursor:
                    row = await obs_cursor.fetchone()
                    if row:
                        obs_id, sid, obs_dt, temp, rain, wind, rh, wd, press = row
                        print(f"   Observation ID: {obs_id}")
                        print(f"   Datetime: {obs_dt}")
                        print(f"   Temperature: {temp}°C")
                        print(f"   Rainfall: {rain}mm")
                        print(f"   Wind Speed: {wind}m/s")
                        print(f"   Relative Humidity: {rh}%")
                        print(f"   Wind Direction: {wd}°")
                        print(f"   Pressure: {press}hPa")

                        # Test 3: Create JSON response
                        print("\n3. JSON Response Format:")
                        response = {
                            "id": obs_id,
                            "station_id": sid,
                            "obs_datetime": obs_dt,
                            "temperature": temp,
                            "relative_humidity": rh,
                            "wind_speed": wind,
                            "wind_direction": wd,
                            "rainfall": rain,
                            "pressure": press
                        }
                        print(json.dumps(response, indent=2))
                    else:
                        print("   ERROR: No observations found!")
                break

        # Test 4: Test historical query
        print("\n4. Testing historical query (Jan 2024 - Mar 2025)...")
        async with db.execute("""
            SELECT COUNT(*) FROM synoptic_observations
            WHERE station_id = (SELECT id FROM stations WHERE code = '23024TEM')
              AND obs_datetime >= '2024-01-01'
              AND obs_datetime <= '2025-03-31'
        """) as cursor:
            count = await cursor.fetchone()
            print(f"   Found {count[0]} observations for Tema in this period")

    print("\n" + "=" * 80)
    print("If you see data above, the API should now work correctly!")
    print("RESTART YOUR API SERVER for changes to take effect:")
    print("  Ctrl+C to stop, then: uvicorn app.main:app --reload")
    print("=" * 80)

asyncio.run(test())
