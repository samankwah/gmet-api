import asyncio
import aiosqlite

async def find_good_observations():
    async with aiosqlite.connect('gmet_weather.db') as db:
        print("Finding observations with temperature data for Tema:")
        print("=" * 80)
        async with db.execute("""
            SELECT id, obs_datetime, temperature, rainfall, wind_speed, relative_humidity
            FROM synoptic_observations
            WHERE station_id = (SELECT id FROM stations WHERE code = '23024TEM')
              AND temperature IS NOT NULL
            ORDER BY obs_datetime DESC
            LIMIT 5
        """) as cursor:
            async for row in cursor:
                obs_id, dt, temp, rain, wind, rh = row
                print(f"ID: {obs_id}")
                print(f"  Date: {dt}")
                print(f"  Temp: {temp}°C, Rain: {rain}mm, Wind: {wind}m/s, RH: {rh}%")
                print()

asyncio.run(find_good_observations())
