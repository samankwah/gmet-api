import asyncio
import aiosqlite

async def check():
    async with aiosqlite.connect('gmet_weather.db') as db:
        print("Observations with actual temperature/wind/humidity data:")
        print("=" * 80)
        async with db.execute('''
            SELECT s.name, s.code, o.obs_datetime,
                   o.temperature, o.rainfall, o.wind_speed, o.relative_humidity
            FROM synoptic_observations o
            JOIN stations s ON o.station_id = s.id
            WHERE o.temperature IS NOT NULL
               OR o.wind_speed IS NOT NULL
               OR o.relative_humidity IS NOT NULL
            ORDER BY o.obs_datetime DESC
            LIMIT 15
        ''') as c:
            async for name, code, dt, temp, rain, wind, rh in c:
                date = dt[:10] if dt else 'N/A'
                print(f"{name:25} ({code:12}) {date}")
                print(f"  Temp: {temp}°C, Rain: {rain}mm, Wind: {wind}m/s, RH: {rh}%\n")

        print("\n" + "=" * 80)
        print("Date range of observations:")
        print("=" * 80)
        async with db.execute('SELECT MIN(obs_datetime), MAX(obs_datetime) FROM synoptic_observations') as c:
            async for min_dt, max_dt in c:
                print(f"  From: {min_dt}")
                print(f"  To:   {max_dt}")

asyncio.run(check())
