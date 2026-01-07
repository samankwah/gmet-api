import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    engine = create_async_engine('sqlite+aiosqlite:///gmet_weather.db')
    async with engine.begin() as conn:
        result = await conn.execute(text('PRAGMA table_info(synoptic_observations)'))
        print("Synoptic Observations Table Structure:")
        print("=" * 60)
        for row in result:
            print(f"Column: {row[1]}, Type: {row[2]}, NotNull: {row[3]}")
    await engine.dispose()

asyncio.run(check())
