# Database Migration Guide: Synoptic Observations Update

This guide explains how to apply the migration that updates the database schema to reflect GMet operational practices.

## Overview

This migration:
- Replaces the generic `observations` table with `synoptic_observations` for SYNOP schedule data
- Adds `daily_summaries` table for aggregated daily statistics
- Migrates existing data from `observations` to `synoptic_observations`
- Updates field types (humidity → relative_humidity as Integer, wind_direction as Integer)

## Pre-Migration Checklist

1. **Backup your database**:
   ```bash
   # PostgreSQL
   pg_dump -U gmet_user gmet_weather > backup_before_migration.sql
   
   # SQLite
   cp gmet_weather.db gmet_weather.db.backup
   ```

2. **Verify current migration state**:
   ```bash
   alembic current
   ```

3. **Review the migration file**:
   - Check `alembic/versions/b3c4d5e6f789_update_to_synoptic_observations_and_daily_summaries.py`
   - Ensure it matches your expectations

## Applying the Migration

### Using Docker

```bash
# Start services (if not already running)
docker-compose up -d

# Apply migration
docker-compose exec api alembic upgrade head

# Verify migration
docker-compose exec api alembic current
```

### Manual Application

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Apply migration
alembic upgrade head

# Verify migration
alembic current
```

## Migration Steps

The migration performs the following operations:

1. **Creates `synoptic_observations` table** with:
   - `obs_datetime` (renamed from `timestamp`)
   - `relative_humidity` (Integer, renamed from `humidity` Float)
   - `wind_direction` (Integer, changed from Float)
   - Unique constraint on `(station_id, obs_datetime)`
   - Appropriate indexes

2. **Migrates data** from `observations` to `synoptic_observations`:
   - Maps `timestamp` → `obs_datetime`
   - Casts `humidity` (Float) → `relative_humidity` (Integer)
   - Casts `wind_direction` (Float) → `wind_direction` (Integer)
   - Preserves all other fields

3. **Creates `daily_summaries` table** with:
   - Daily aggregated statistics
   - Unique constraint on `(station_id, date)`
   - Appropriate indexes

4. **Drops old `observations` table** and its indexes

## Verification

After migration, verify the changes:

```sql
-- Check synoptic_observations table exists
SELECT COUNT(*) FROM synoptic_observations;

-- Check daily_summaries table exists
SELECT COUNT(*) FROM daily_summaries;

-- Verify data migration
SELECT 
    COUNT(*) as total_observations,
    MIN(obs_datetime) as earliest,
    MAX(obs_datetime) as latest
FROM synoptic_observations;

-- Check unique constraint
SELECT station_id, obs_datetime, COUNT(*)
FROM synoptic_observations
GROUP BY station_id, obs_datetime
HAVING COUNT(*) > 1;
-- Should return 0 rows
```

## Rollback (If Needed)

If you need to rollback the migration:

```bash
# Rollback one migration
alembic downgrade -1

# Or rollback to specific revision
alembic downgrade acb5aa092b78
```

**Note**: The rollback will:
- Recreate the old `observations` table
- Migrate data back from `synoptic_observations` to `observations`
- Drop `synoptic_observations` and `daily_summaries` tables

## Post-Migration Tasks

1. **Update application code**:
   - Replace references to `Observation` with `SynopticObservation`
   - Update field names: `timestamp` → `obs_datetime`, `humidity` → `relative_humidity`
   - Update CRUD operations and schemas

2. **Update API endpoints**:
   - Modify endpoints to use new model names
   - Update response schemas

3. **Test the application**:
   - Verify data retrieval works correctly
   - Test API endpoints
   - Run test suite

## Troubleshooting

### Migration Fails with Unique Constraint Error

If you have duplicate `(station_id, timestamp)` pairs in the old `observations` table:

```sql
-- Find duplicates
SELECT station_id, timestamp, COUNT(*)
FROM observations
GROUP BY station_id, timestamp
HAVING COUNT(*) > 1;

-- Remove duplicates (keep the most recent)
DELETE FROM observations
WHERE id NOT IN (
    SELECT MAX(id)
    FROM observations
    GROUP BY station_id, timestamp
);
```

Then retry the migration.

### Data Type Conversion Errors

If you have invalid data types:

```sql
-- Check for invalid humidity values
SELECT id, humidity FROM observations
WHERE humidity IS NOT NULL
  AND (humidity < 0 OR humidity > 100 OR humidity != CAST(humidity AS INTEGER));

-- Check for invalid wind_direction values
SELECT id, wind_direction FROM observations
WHERE wind_direction IS NOT NULL
  AND (wind_direction < 0 OR wind_direction > 360);
```

Fix the data before migration.

### Foreign Key Constraint Errors

Ensure all `station_id` values in `observations` reference existing stations:

```sql
-- Find orphaned observations
SELECT o.id, o.station_id
FROM observations o
LEFT JOIN stations s ON o.station_id = s.id
WHERE s.id IS NULL;
```

Delete or fix orphaned records before migration.

## Support

If you encounter issues:
1. Check the migration logs
2. Review the error messages
3. Verify your database backup is valid
4. Contact the development team

## Migration File Details

- **Revision ID**: `b3c4d5e6f789`
- **Previous Revision**: `822df6608e6c`
- **File**: `alembic/versions/b3c4d5e6f789_update_to_synoptic_observations_and_daily_summaries.py`

