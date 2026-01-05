"""Quick database check script - simpler version"""

import sqlite3

conn = sqlite3.connect('gmet_weather.db')
cursor = conn.cursor()

print("Tables in database:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for table in cursor.fetchall():
    print(f"  - {table[0]}")

print("\nMigration version:")
cursor.execute("SELECT version_num FROM alembic_version")
version = cursor.fetchone()
print(f"  {version[0] if version else 'Not found'}")

print("\nRecord counts:")
for table in ['stations', 'synoptic_observations', 'daily_summaries']:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} records")
    except:
        print(f"  {table}: table not found")

conn.close()

