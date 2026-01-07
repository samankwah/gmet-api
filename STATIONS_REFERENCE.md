# GMet Weather API - Stations Reference Guide

## Current Database Status

Your database currently has:
- **663 stations** imported
- **Observations**: Import in progress

## Available API Endpoints

### 1. List All Stations

```http
GET http://127.0.0.1:8000/api/v1/weather/stations
Headers:
  X-API-Key: e4oV7CpCNlIgpq4HZ1Tlk1z2dl5Cf7RT
```

Returns all stations with pagination (default limit: 100)

### 2. Get Current Weather

```http
GET http://127.0.0.1:8000/v1/current?location=Tema
Headers:
  X-API-Key: e4oV7CpCNlIgpq4HZ1Tlk1z2dl5Cf7RT
```

You can use either:
- Station name: `location=Tema`, `location=Accra`, `location=Kumasi`
- Station code: `location=23024TEM`, `location=23016ACC`

### 3. Get Historical Data

```http
GET http://127.0.0.1:8000/v1/historical?station=Tema&start=2024-01-01&end=2024-12-31&param=rainfall
Headers:
  X-API-Key: e4oV7CpCNlIgpq4HZ1Tlk1z2dl5Cf7RT
```

Parameters:
- `station`: Station code or name (required)
- `start`: Start date YYYY-MM-DD (required)
- `end`: End date YYYY-MM-DD (required)
- `param`: Specific parameter like 'rainfall', 'temperature', 'humidity' (optional)
- `limit`: Max records (default: 1000)

## Sample Station Codes

Here are some major stations you can test with:

| Station Name | Station Code | Region | Lat | Lon |
|-------------|--------------|---------|-----|-----|
| Tema | 23024TEM | Greater Accra | 5.6667 | 0.0167 |
| KIAMO-Accra | 23016ACC | Greater Accra | 5.6098 | -0.1680 |
| Kumasi | 17009KSI | Ashanti | 6.7167 | -1.6333 |
| Tamale | 07006TLE | Northern | 9.4000 | -0.8500 |
| Takoradi | 23003TDI | Western | 4.8833 | -1.7500 |
| Cape Coast | 23013CAP | Central | 5.1151 | -1.2500 |
| Ho | 07017HO- | Volta | 6.6000 | 0.4667 |
| Bolgatanga | 04003BOL | Upper East | 10.7833 | -0.8500 |
| Wa | 02000WAL | Upper West | 10.0500 | -2.5000 |
| Sunyani | 01018SUN | Bono | 7.3333 | -2.3333 |

## Testing the API

### Test 1: List Stations

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/weather/stations" \
  -H "X-API-Key: e4oV7CpCNlIgpq4HZ1Tlk1z2dl5Cf7RT"
```

Expected: List of stations with their codes, names, and coordinates

### Test 2: Current Weather (after observations import completes)

```bash
curl -X GET "http://127.0.0.1:8000/v1/current?location=Tema" \
  -H "X-API-Key: e4oV7CpCNlIgpq4HZ1Tlk1z2dl5Cf7RT"
```

Expected: Latest weather observation for Tema station

### Test 3: Historical Data (after observations import completes)

```bash
curl -X GET "http://127.0.0.1:8000/v1/historical?station=Accra&start=2024-01-01&end=2024-01-31" \
  -H "X-API-Key: e4oV7CpCNlIgpq4HZ1Tlk1z2dl5Cf7RT"
```

Expected: Weather observations for January 2024

## Why Am I Getting Empty Arrays?

If you're getting empty arrays (`[]`), it means:

1. **For `/v1/current`**: No observations exist for that station yet
2. **For `/v1/historical`**: No observations exist for that station and date range

## Current Import Status

The observation data import is currently running in the background. This process:
- Reads 135,902 rows from `gmet_synoptic_data.csv`
- Processes data from 1960-2025
- Imports observations for all 44 stations in the CSV
- Takes approximately 10-15 minutes to complete

### Check Import Progress

Run this command to check how many observations have been imported:

```bash
python check_db_data.py
```

This will show:
- Number of stations (should be 663)
- Number of observations (will increase as import runs)
- Sample observation data

## Data Structure

### Station Response
```json
{
  "id": 1,
  "code": "23024TEM",
  "name": "Tema",
  "latitude": 5.6667,
  "longitude": 0.0167,
  "region": "Greater Accra",
  "created_at": "2026-01-06T...",
  "updated_at": "2026-01-06T..."
}
```

### Observation Response
```json
{
  "id": 1,
  "station_id": 1,
  "obs_datetime": "2024-01-01T12:00:00+00:00",
  "element": "RR",
  "value": 15.5,
  "created_at": "2026-01-06T...",
  "updated_at": "2026-01-06T..."
}
```

## Weather Elements

The CSV data includes these weather parameters:

| Element ID | Description | Unit |
|------------|-------------|------|
| RR | Rainfall/Precipitation | mm |
| Tx | Maximum Temperature | °C |
| Tn | Minimum Temperature | °C |
| Kts | Wind Speed | knots |
| RH | Relative Humidity | % |
| SUNHR | Sunshine Hours | hours |

## Next Steps

1. **Wait for import to complete** (check with `python check_db_data.py`)
2. **Test the stations endpoint** (works now with 663 stations)
3. **Test current/historical endpoints** (will work after import completes)
4. **Monitor the import progress** using the check script

## Troubleshooting

### Empty Arrays for Historical Data

**Problem**: Getting `[]` for `/v1/historical?station=Accra&start=2024-01-01&end=2024-12-31`

**Solutions**:
1. Check if observations import completed: `python check_db_data.py`
2. Verify the station code exists: Check stations list first
3. Try a different date range: Data is from 1960-2025, ensure your dates are in that range
4. Check station name spelling: "KIAMO-Accra" vs "Accra"

### 404 Errors

**Problem**: "Location not found"

**Solutions**:
1. List all stations first to get correct codes/names
2. Use exact station code from the database
3. Station names are case-insensitive but must match

### Rate Limit Errors

**Problem**: "Too many requests"

**Solution**: Wait a minute between requests. Limits are:
- `/v1/current`: 100 requests/minute
- `/v1/historical`: 100 requests/minute
- `/api/v1/weather/stations`: Default rate limit

## Questions?

- Check `check_db_data.py` output to see current database state
- The import script logs progress every 100 groups processed
- All API endpoints require the `X-API-Key` header
