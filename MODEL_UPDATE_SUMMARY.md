# Database Model Update Summary

## Overview

The database models have been updated to accurately reflect GMet operational practices:

- Automatic weather stations transmit at fixed times: **0600, 0900, 1200, 1500 UTC**
- Observations follow the standard **SYNOP reporting schedule**
- Daily summaries aggregate data for public bulletins and climatology

## Files Created

### New Model Files

1. **`app/models/station.py`**

   - Extracted Station model with updated relationships
   - Relationships: `synoptic_observations`, `daily_summaries`

2. **`app/models/synoptic_observation.py`**

   - Replaces generic `Observation` model
   - Fields: `obs_datetime`, `temperature`, `relative_humidity` (Integer), `wind_speed`, `wind_direction` (Integer), `pressure`, `rainfall`
   - Unique constraint: `(station_id, obs_datetime)`
   - Indexes optimized for time-series queries

3. **`app/models/daily_summary.py`**
   - New model for daily aggregated statistics
   - Fields: `date`, `temp_max`, `temp_max_time`, `temp_min`, `temp_min_time`, `rainfall_total`, `mean_rh`, `max_wind_gust`
   - Unique constraint: `(station_id, date)`

### Updated Files

4. **`app/models/__init__.py`**

   - Updated imports to use new models
   - Provides backward compatibility alias: `Observation = SynopticObservation`

5. **`app/models/weather_data.py`**

   - Converted to compatibility module
   - Re-exports new models for backward compatibility

6. **`alembic/env.py`**

   - Updated to import new models: `Station`, `SynopticObservation`, `DailySummary`

7. **`alembic/versions/b3c4d5e6f789_update_to_synoptic_observations_and_daily_summaries.py`**

   - Migration file that:
     - Creates `synoptic_observations` table
     - Creates `daily_summaries` table
     - Migrates data from `observations` to `synoptic_observations`
     - Drops old `observations` table

8. **`README.md`**

   - Added "Data Model – GMet Synoptic Schedule" section
   - Updated database schema documentation

9. **`MIGRATION_GUIDE.md`**
   - Comprehensive migration guide with commands and troubleshooting

## Key Changes

### Field Name Changes

| Old Field                | New Field                     | Notes                 |
| ------------------------ | ----------------------------- | --------------------- |
| `timestamp`              | `obs_datetime`                | More descriptive name |
| `humidity` (Float)       | `relative_humidity` (Integer) | Type change + rename  |
| `wind_direction` (Float) | `wind_direction` (Integer)    | Type change           |

### New Constraints

- **SynopticObservation**: Unique on `(station_id, obs_datetime)`
- **DailySummary**: Unique on `(station_id, date)`

### New Indexes

- `idx_synoptic_station_datetime` on `(station_id, obs_datetime)`
- `idx_synoptic_datetime_station` on `(obs_datetime, station_id)`
- `idx_daily_station_date` on `(station_id, date)`

## Commands to Apply Migration

### Using Docker

```bash
# 1. Backup database (recommended)
docker-compose exec db pg_dump -U gmet_user gmet_weather > backup.sql

# 2. Apply migration
docker-compose exec api alembic upgrade head

# 3. Verify migration
docker-compose exec api alembic current
```

### Manual Application

```bash
# 1. Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 2. Backup database (recommended)
# PostgreSQL:
pg_dump -U gmet_user gmet_weather > backup.sql
# SQLite:
cp gmet_weather.db gmet_weather.db.backup

# 3. Apply migration
alembic upgrade head

# 4. Verify migration
alembic current
```

## Expected Output

After running `alembic upgrade head`, you should see:

```
INFO  [alembic.runtime.migration] Context impl AsyncImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 822df6608e6c -> b3c4d5e6f789, Update to synoptic observations at 0600/0900/1200/1500 and daily summaries
```

Verify with:

```bash
alembic current
# Should show: b3c4d5e6f789 (head)
```

## Verification Queries

After migration, run these SQL queries to verify:

```sql
-- Check tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('synoptic_observations', 'daily_summaries');

-- Check data migration
SELECT COUNT(*) FROM synoptic_observations;

-- Check unique constraint
SELECT station_id, obs_datetime, COUNT(*)
FROM synoptic_observations
GROUP BY station_id, obs_datetime
HAVING COUNT(*) > 1;
-- Should return 0 rows

-- Check indexes
SELECT indexname
FROM pg_indexes
WHERE tablename IN ('synoptic_observations', 'daily_summaries');
```

## Backward Compatibility

The update maintains backward compatibility:

- `from app.models.weather_data import Observation` still works
- `Observation` is an alias for `SynopticObservation`
- Existing code using `Observation` will continue to work

**However**, you should update code to use:

- `SynopticObservation` instead of `Observation`
- `obs_datetime` instead of `timestamp`
- `relative_humidity` instead of `humidity`

## Next Steps

After applying the migration:

1. **Update application code**:

   - Update CRUD operations to use `SynopticObservation`
   - Update schemas to use new field names
   - Update API endpoints

2. **Test the application**:

   - Run test suite
   - Verify data retrieval
   - Test API endpoints

3. **Update documentation**:
   - Update API documentation
   - Update integration guides

## Rollback (If Needed)

If you need to rollback:

```bash
# Rollback one migration
alembic downgrade -1

# Or rollback to specific revision
alembic downgrade 822df6608e6c
```

**Warning**: Rollback will:

- Recreate old `observations` table
- Migrate data back (with type conversions)
- Drop `synoptic_observations` and `daily_summaries` tables

## Support

For issues or questions:

1. Check `MIGRATION_GUIDE.md` for detailed troubleshooting
2. Review migration logs
3. Verify database backup is valid
4. Contact development team

## Model Relationships

```
Station
├── synoptic_observations (1:many)
│   └── obs_datetime: 0600, 0900, 1200, 1500 UTC
└── daily_summaries (1:many)
    └── date: Daily aggregated statistics
```

## Validation Notes

Future implementations can add validators to:

- Ensure `obs_datetime.hour` is in `[6, 9, 12, 15]` for SYNOP schedule
- Validate `relative_humidity` is in range `[0, 100]`
- Validate `wind_direction` is in range `[0, 360]`

These validations can be added at the Pydantic schema level or as database constraints.
