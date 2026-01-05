# GMet CLIDATA Import Guide

This document explains how to import historical climate data from Ghana Meteorological Agency (GMet) CLIDATA format into the GMet Weather API database.

## CLIDATA Format Overview

The GMet CLIDATA CSV format uses a **wide format** where each row represents one month of data for a specific:

- **Station** (identified by Station ID)
- **Element** (weather parameter, e.g., "Kts" for wind speed)
- **Year** and **Month**
- **Time** (observation time, e.g., "09:00")

### CSV Structure

| Column     | Description                        | Example                     |
| ---------- | ---------------------------------- | --------------------------- |
| Station ID | GMet internal station identifier   | "23024TEM"                  |
| Element ID | Weather parameter code             | "Kts", "Temp", "RH", "Rain" |
| Year       | Year of observation                | "2013"                      |
| Month      | Month (01-12)                      | "01"                        |
| Time       | Observation time (HH:MM)           | "09:00"                     |
| Data Type  | Data type indicator                | "N"                         |
| 01-31      | Daily values for each day of month | Numeric values or empty     |
| Geogr1     | Latitude                           | 0.001579                    |
| Geogr2     | Longitude                          | 5.632253                    |
| Name       | Station name                       | "Tema"                      |

### Example Row

```csv
"Station ID","Element ID","Year","Month","Time","Data Type","01","02","03",...,"31","Geogr1","Geogr2","Name"
"23024TEM","Kts","2013","01","09:00","N",6,3,3,4,4,3,5,2,4,4,5,3,3,6,6,5,3,5,6,6,6,4,5,5,7,6,5,4,5,4,5,0.001579,5.632253,"Tema"
```

This row represents:

- **Station**: Tema (23024TEM)
- **Parameter**: Wind speed in knots (Kts)
- **Period**: January 2013, 09:00 observations
- **Daily values**: Day 1 = 6 knots, Day 2 = 3 knots, etc.

## Element ID Mappings

The import script maps GMet Element IDs to database fields:

| Element ID | Database Field | Unit Conversion            |
| ---------- | -------------- | -------------------------- |
| Kts        | wind_speed     | Knots → m/s (× 0.514444)   |
| Temp       | temperature    | Celsius (no conversion)    |
| RH         | humidity       | Percentage (no conversion) |
| Rain       | rainfall       | mm (no conversion)         |
| Pressure   | pressure       | hPa (no conversion)        |
| WindDir    | wind_direction | Degrees (no conversion)    |

## Station ID Mappings

The script maps GMet Station IDs to database station codes:

| GMet Station ID | Database Code | Station Name        |
| --------------- | ------------- | ------------------- |
| 23024TEM        | DGTM          | Tema                |
| 23022SAL        | DGSP          | Saltpond            |
| 23016ACC        | DGAA          | Accra (KIAMO-Accra) |
| 23003TDI        | DGTK          | Takoradi            |

**Note**: If a station ID is not in the mapping, the script will attempt to find the station by name. If not found, observations for that station will be skipped.

## Usage

### Basic Import

```bash
# Activate virtual environment (if using one)
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Run import script
python -m scripts.import_gmet_clidata "path/to/Rdata_ALL List 1.csv"
```

### Dry Run (Test Without Committing)

```bash
# Test the import without committing to database
python -m scripts.import_gmet_clidata "path/to/Rdata_ALL List 1.csv" --dry-run
```

### Custom Batch Size

```bash
# Process 500 rows before each commit (default is 1000)
python -m scripts.import_gmet_clidata "path/to/Rdata_ALL List 1.csv" --batch-size 500
```

### Full Example

```bash
# Import with custom settings
python -m scripts.import_gmet_clidata \
    "C:\Users\CRAFT\OneDrive - Smart Workplace\Documents\dataset\Excel\Rdata_ALL List 1.csv" \
    --batch-size 2000
```

## How It Works

1. **Reads CSV file** row by row
2. **Maps Station IDs** to database station codes
3. **Maps Element IDs** to database fields with unit conversions
4. **Expands wide format** into individual daily observations
5. **Creates timestamps** from Year, Month, Day, and Time
6. **Handles missing data** (empty strings, 0 values are skipped)
7. **Updates existing observations** or creates new ones
8. **Commits in batches** for performance

## Data Quality

### Missing Data Handling

- Empty strings (`""`) are treated as missing data
- Zero values (`0`) are treated as missing data
- Missing data is skipped (not inserted as NULL)

### Duplicate Handling

- If an observation already exists (same station, timestamp), it is **updated** with new values
- This allows re-importing data to correct errors

### Validation

- Invalid timestamps are logged and skipped
- Invalid numeric values are logged and skipped
- Stations without mappings are logged and skipped

## Output

The script provides detailed logging:

```
INFO: Starting CLIDATA import from: Rdata_ALL List 1.csv
INFO: Dry run: False, Batch size: 1000
INFO: Processed 1000 rows, created 15000 observations
INFO: Processed 2000 rows, created 30000 observations
...
INFO: Final commit completed
INFO: ============================================================
INFO: Import Statistics:
INFO:   Rows processed: 505290
INFO:   Observations created: 1250000
INFO:   Errors: 0
INFO:   Stations found: 15
INFO:   Elements processed: Kts, Temp, RH, Rain
INFO: ============================================================
```

## Troubleshooting

### Station Not Found

If you see warnings like:

```
WARNING: No station code mapping for GMet ID 23002ADA (Ada). Skipping observations.
```

**Solution**: Add the station mapping to `STATION_ID_MAPPING` in `scripts/import_gmet_clidata.py` or ensure the station exists in the database.

### Unknown Element ID

If you see:

```
DEBUG: Skipping unknown element: UnknownElement
```

**Solution**: Add the element mapping to `ELEMENT_MAPPING` in `scripts/import_gmet_clidata.py`.

### Invalid Timestamps

If you see timestamp errors:

```
ERROR: Error parsing timestamp: year=2013, month=13, day=1, time=09:00
```

**Solution**: Check the CSV data for invalid dates (e.g., month 13, day 32).

### Performance

For large files (500K+ rows):

- Use larger batch sizes (2000-5000) for better performance
- Monitor database connection pool size
- Consider running during off-peak hours

## Adding New Element Mappings

To add support for new weather parameters:

1. Edit `scripts/import_gmet_clidata.py`
2. Add to `ELEMENT_MAPPING`:

```python
ELEMENT_MAPPING: Dict[str, Tuple[str, callable]] = {
    # ... existing mappings ...
    "NewElement": ("database_field", conversion_function),
}
```

Example:

```python
"SolarRad": ("solar_radiation", lambda x: float(x) * 0.001),  # W/m² to kW/m²
```

## Adding New Station Mappings

To add support for new stations:

1. Edit `scripts/import_gmet_clidata.py`
2. Add to `STATION_ID_MAPPING`:

```python
STATION_ID_MAPPING: Dict[str, str] = {
    # ... existing mappings ...
    "23002ADA": "DGAD",  # Ada
}
```

Or ensure the station exists in the database with a matching name.

## Best Practices

1. **Always run a dry-run first** to check for errors
2. **Backup your database** before importing large datasets
3. **Import in stages** if the file is very large (split by year/station)
4. **Monitor logs** for warnings and errors
5. **Verify data** after import using the API endpoints

## Related Documentation

- [API Documentation](../README.md)
- [Database Schema](../app/models/weather_data.py)
- [Station Seeding](../scripts/seed_ghana_stations.py)
