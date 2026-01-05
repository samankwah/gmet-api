"""
Quick script to test and verify the database state after migration.

Run this to check:
- Migration status
- Tables exist
- Data was migrated
- Sample data from new tables
"""

import sqlite3
import sys
from pathlib import Path

# Database path
db_path = Path("gmet_weather.db")

if not db_path.exists():
    print("[ERROR] Database file not found!")
    sys.exit(1)

print("=" * 60)
print("DATABASE STATE VERIFICATION")
print("=" * 60)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# 1. Check all tables
print("\n1. TABLES IN DATABASE:")
print("-" * 60)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
for table in tables:
    print(f"  [OK] {table[0]}")

# 2. Check migration version
print("\n2. ALEMBIC VERSION:")
print("-" * 60)
try:
    cursor.execute("SELECT version_num FROM alembic_version")
    version = cursor.fetchone()
    if version:
        print(f"  Current migration: {version[0]}")
    else:
        print("  No migration version found")
except sqlite3.OperationalError:
    print("  alembic_version table not found")

# 3. Check synoptic_observations table structure
print("\n3. SYNOPTIC_OBSERVATIONS TABLE:")
print("-" * 60)
try:
    cursor.execute("PRAGMA table_info(synoptic_observations)")
    columns = cursor.fetchall()
    print(f"  Columns ({len(columns)}):")
    for col in columns:
        col_name, col_type = col[1], col[2]
        nullable = "NULL" if col[3] == 0 else "NOT NULL"
        print(f"    - {col_name}: {col_type} ({nullable})")
    
    # Count records
    cursor.execute("SELECT COUNT(*) FROM synoptic_observations")
    count = cursor.fetchone()[0]
    print(f"  Total records: {count}")
    
    # Sample data
    if count > 0:
        cursor.execute("SELECT id, station_id, obs_datetime, temperature, relative_humidity FROM synoptic_observations LIMIT 3")
        samples = cursor.fetchall()
        print(f"  Sample records:")
        for sample in samples:
            print(f"    ID: {sample[0]}, Station: {sample[1]}, DateTime: {sample[2]}, Temp: {sample[3]}, RH: {sample[4]}")
except sqlite3.OperationalError as e:
    print(f"  [ERROR] Table not found or error: {e}")

# 4. Check daily_summaries table structure
print("\n4. DAILY_SUMMARIES TABLE:")
print("-" * 60)
try:
    cursor.execute("PRAGMA table_info(daily_summaries)")
    columns = cursor.fetchall()
    print(f"  Columns ({len(columns)}):")
    for col in columns:
        col_name, col_type = col[1], col[2]
        nullable = "NULL" if col[3] == 0 else "NOT NULL"
        print(f"    - {col_name}: {col_type} ({nullable})")
    
    # Count records
    cursor.execute("SELECT COUNT(*) FROM daily_summaries")
    count = cursor.fetchone()[0]
    print(f"  Total records: {count}")
except sqlite3.OperationalError as e:
    print(f"  [ERROR] Table not found or error: {e}")

# 5. Check stations table
print("\n5. STATIONS TABLE:")
print("-" * 60)
try:
    cursor.execute("SELECT COUNT(*) FROM stations")
    count = cursor.fetchone()[0]
    print(f"  Total stations: {count}")
    
    if count > 0:
        cursor.execute("SELECT id, code, name, region FROM stations LIMIT 5")
        stations = cursor.fetchall()
        print(f"  Sample stations:")
        for station in stations:
            print(f"    {station[1]} ({station[2]}) - {station[3]}")
except sqlite3.OperationalError as e:
    print(f"  [ERROR] Error: {e}")

# 6. Check for old observations table (should not exist)
print("\n6. OLD OBSERVATIONS TABLE:")
print("-" * 60)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='observations'")
old_table = cursor.fetchone()
if old_table:
    print("  ⚠️  WARNING: Old 'observations' table still exists!")
else:
    print("  [OK] Old 'observations' table removed (as expected)")

# 7. Check indexes
print("\n7. INDEXES ON SYNOPTIC_OBSERVATIONS:")
print("-" * 60)
cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='synoptic_observations'")
indexes = cursor.fetchall()
for idx in indexes:
    print(f"  [OK] {idx[0]}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)

conn.close()

