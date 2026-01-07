import asyncio
import aiosqlite

async def check_samples():
    async with aiosqlite.connect('gmet_weather.db') as db:
        # Get stations with data
        print("Stations with observation data (first 20):")
        print("=" * 80)
        async with db.execute('''
            SELECT DISTINCT s.name, s.code
            FROM synoptic_observations o
            JOIN stations s ON o.station_id = s.id
            ORDER BY s.name
            LIMIT 20
        ''') as cursor:
            async for name, code in cursor:
                print(f"  {name:30} (Code: {code})")

        print("\n" + "=" * 80)
        print("Sample observations (most recent):")
        print("=" * 80)
        async with db.execute('''
            SELECT s.name, s.code, o.obs_datetime, o.temperature,
                   o.rainfall, o.wind_speed, o.relative_humidity
            FROM synoptic_observations o
            JOIN stations s ON o.station_id = s.id
            ORDER BY o.obs_datetime DESC
            LIMIT 15
        ''') as cursor:
            async for row in cursor:
                name, code, dt, temp, rain, wind, rh = row
                print(f"  {name} ({code})")
                print(f"    Date: {dt}")
                print(f"    Temp: {temp}°C, Rain: {rain}mm, Wind: {wind}m/s, RH: {rh}%")
                print()

asyncio.run(check_samples())
