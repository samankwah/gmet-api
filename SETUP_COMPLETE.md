# GMet Weather API - Setup Complete

## Summary

The GMet Weather API is now fully operational with corrected data for 23 weather stations across Ghana, spanning 1960-2025.

---

## Database Status

### Current Statistics
- **Stations**: 23 weather stations
- **Daily Summaries**: 527,918 records
- **Synoptic Observations**: 1,593,482 records
- **Date Range**: 1960-01-01 to 2025-05-31
- **Database File**: `gmet_weather.db` (SQLite)

### Station List (All 23 Stations)
1. 14067ABE - Abetifi
2. 23002ADA - Ada
3. 15076AKA - Akatsi
4. 21088ODA - Akim Oda
5. 07003AKU - Akuse
6. 23001AXM - Axim
7. 07000BOL - Bole
8. 07017HO- - Ho
9. 07058HO- - Ho (alternate)
10. 07008KRA - Kete-Krachi
11. 23016ACC - KIAMO-Accra
12. 22050KDA - Koforidua
13. 17009KSI - Kumasi
14. 04003NAV - Navrongo
15. 23022SAL - Saltpond
16. 16015BEK - Sefwi Bekwai
17. 01032SUN - Sunyani
18. 23003TDI - Takoradi
19. 07006TLE - Tamale
20. 23024TEM - Tema
21. 01013WA- - Wa
22. 01018WEN - Wenchi
23. 08010YDI - Yendi

---

## API Authentication

### API Key
```
2835b0ba074a0e24ba0e98f9d7046475
```

**IMPORTANT**: Use this key in all API requests via the `X-API-Key` header.

---

## Testing the API

### Server Information
- **URL**: `http://localhost:8000`
- **Port**: 8000
- **Status**: Running

### Example API Requests

#### 1. Get Historical Data (Daily) - Recent Year
```bash
curl -H "X-API-Key: 2835b0ba074a0e24ba0e98f9d7046475" \
  "http://localhost:8000/v1/historical?station=tema&start=2022-01-01&end=2022-01-31&granularity=daily&limit=10"
```

**Response**: Returns daily weather summaries for Tema in January 2022

#### 2. Get Historical Data - 1980s
```bash
curl -H "X-API-Key: 2835b0ba074a0e24ba0e98f9d7046475" \
  "http://localhost:8000/v1/historical?station=accra&start=1985-01-01&end=1985-12-31&granularity=daily&limit=100"
```

**Response**: Returns 1985 data for Accra

#### 3. Get Historical Data - 2000s
```bash
curl -H "X-API-Key: 2835b0ba074a0e24ba0e98f9d7046475" \
  "http://localhost:8000/v1/historical?station=kumasi&start=2005-06-01&end=2005-06-30&granularity=daily&limit=50"
```

**Response**: Returns June 2005 data for Kumasi

#### 4. Get Synoptic Observations (Time-Specific)
```bash
curl -H "X-API-Key: 2835b0ba074a0e24ba0e98f9d7046475" \
  "http://localhost:8000/v1/historical?station=tema&start=2022-01-01&end=2022-01-02&granularity=synoptic&limit=10"
```

**Response**: Returns 4x daily observations at 06:00, 09:00, 12:00, 15:00 UTC

#### 5. Filter by Specific Parameter (Rainfall)
```bash
curl -H "X-API-Key: 2835b0ba074a0e24ba0e98f9d7046475" \
  "http://localhost:8000/v1/historical?station=wa&start=2010-01-01&end=2010-12-31&param=rainfall&limit=100"
```

**Response**: Returns rainfall data for Wa in 2010

---

## Testing in Swagger UI

1. **Open Swagger UI**: `http://localhost:8000/docs`
2. **Click "Authorize"** button (top right)
3. **Enter API Key**: `2835b0ba074a0e24ba0e98f9d7046475`
4. **Click "Authorize"** then "Close"
5. **Test any endpoint** - all are now authenticated

### Example Swagger Test
1. Navigate to `/v1/historical`
2. Click "Try it out"
3. Fill in parameters:
   - station: `tema`
   - start: `2022-01-01`
   - end: `2022-01-31`
   - granularity: `daily`
   - limit: `10`
4. Click "Execute"
5. View response with weather data

---

## Testing in Postman

### Setup
1. Create new request in Postman
2. Method: `GET`
3. URL: `http://localhost:8000/v1/historical`
4. Headers:
   - Key: `X-API-Key`
   - Value: `2835b0ba074a0e24ba0e98f9d7046475`
5. Params:
   - `station`: tema
   - `start`: 2022-01-01
   - `end`: 2022-01-31
   - `granularity`: daily
   - `limit`: 10
6. Click "Send"

### Expected Response (200 OK)
```json
[
  {
    "id": 123,
    "station_id": 20,
    "obs_datetime": "2022-01-01T12:00:00Z",
    "temperature": 29.65,
    "relative_humidity": 74,
    "wind_speed": 2.06,
    "rainfall": 0.0,
    "temp_min": 24.1,
    "temp_max": 31.2,
    "rh_0600": 85,
    "rh_0900": 78,
    "rh_1200": 65,
    "rh_1500": 72
  },
  ...
]
```

---

## Verification Scripts

### 1. Verify Station Count
```bash
cd "C:\Users\CRAFT\Desktop\future MEST projects\Backend\met-api"
python verify_station_count.py
```

**Expected Output**:
```
============================================================
STATION COUNT VERIFICATION
============================================================
Stations in database:           23
Stations with weather data:     23
Unique stations in CSV:         23

Daily summaries:                527,918
Synoptic observations:          1,593,482
============================================================

[OK] CSV station count is correct (23)
[OK] Database stations match CSV
```

### 2. Query Database Directly
```bash
python -c "
import sqlite3
conn = sqlite3.connect('gmet_weather.db')
cursor = conn.cursor()

# Check stations
cursor.execute('SELECT code, name FROM stations LIMIT 10')
print('First 10 stations:')
for code, name in cursor.fetchall():
    print(f'  {code} - {name}')

# Check date range
cursor.execute('SELECT MIN(date), MAX(date) FROM daily_summaries')
print(f'\nDate range: {cursor.fetchone()}')

conn.close()
"
```

---

## Changes Made

### 1. Code Updates
- **import_all_historical_data.py**: Updated station count from "663" to "23"
- **scripts/import_hybrid_weather_data.py**:
  - Added station count reporting
  - Added date validation to skip invalid dates (e.g., Feb 30, Apr 31)
- **verify_station_count.py**: Created verification script

### 2. Data Updates
- CSV corrected from 43 stations to 23 stations
- Database rebuilt from scratch with correct data
- All 23 stations seeded with proper metadata

### 3. Database Setup
- Fresh database created with proper schema
- API keys regenerated
- 527,918 daily summaries imported
- 1,593,482 synoptic observations imported

---

## File Locations

```
met-api/
├── gmet_weather.db                    # SQLite database (active)
├── gmet_synoptic_data.csv             # Source CSV (23 stations, 116,913 rows)
├── import_all_historical_data.py      # Import script (updated)
├── seed_stations_from_csv.py          # Station seeding script (new)
├── verify_station_count.py            # Verification script (new)
├── SETUP_COMPLETE.md                  # This file
│
├── backups/
│   └── gmet_weather_backup_*.db       # Database backup
│
└── scripts/
    ├── import_hybrid_weather_data.py  # Main import logic (updated)
    └── seed_api_keys.py               # API key seeding
```

---

## Available Weather Parameters

### Daily Summaries (granularity=daily)
- `temperature` - Mean daily temperature (°C)
- `temp_min` - Minimum temperature (°C)
- `temp_max` - Maximum temperature (°C)
- `rainfall` / `rainfall_total` - Total daily rainfall (mm)
- `relative_humidity` / `mean_rh` - Mean relative humidity (%)
- `rh_0600` - RH at 06:00 UTC (%)
- `rh_0900` - RH at 09:00 UTC (%)
- `rh_1200` - RH at 12:00 UTC (%)
- `rh_1500` - RH at 15:00 UTC (%)
- `wind_speed` - Mean wind speed (m/s)
- `wind_direction` - Wind direction (degrees)
- `pressure` - Atmospheric pressure (hPa)
- `sunshine_hours` - Sunshine duration (hours)

### Synoptic Observations (granularity=synoptic)
- Same parameters as daily summaries
- 4 observations per day at 06:00, 09:00, 12:00, 15:00 UTC

---

## Query Parameters

### /v1/historical Endpoint

| Parameter | Required | Type | Description | Example |
|-----------|----------|------|-------------|---------|
| station | Yes | string | Station name or code | `tema`, `accra`, `kumasi` |
| start | Yes | string | Start date (YYYY-MM-DD) | `2022-01-01` |
| end | Yes | string | End date (YYYY-MM-DD) | `2022-12-31` |
| granularity | No | string | `daily` or `synoptic` | `daily` (default) |
| param | No | string | Filter by parameter | `rainfall`, `temperature` |
| limit | No | integer | Max records (1-10000) | `100` (default: 1000) |
| skip | No | integer | Skip N records | `0` (default: 0) |

---

## Troubleshooting

### API Returns 401 Unauthorized
**Solution**: Check API key in header
```bash
curl -H "X-API-Key: 2835b0ba074a0e24ba0e98f9d7046475" http://localhost:8000/v1/historical?...
```

### API Returns Empty Array []
**Possible causes**:
1. Station name incorrect (use lowercase: `tema` not `Tema`)
2. Date range has no data
3. Station doesn't exist in database

**Check available stations**:
```bash
python -c "
import sqlite3
conn = sqlite3.connect('gmet_weather.db')
cursor = conn.cursor()
cursor.execute('SELECT code, name FROM stations')
for code, name in cursor.fetchall():
    print(f'{code} - {name}')
conn.close()
"
```

### Server Not Running
**Start server**:
```bash
cd "C:\Users\CRAFT\Desktop\future MEST projects\Backend\met-api"
python -m uvicorn app.main:app --reload --port 8000
```

---

## Success Metrics

- ✅ 23 stations with complete data (1960-2025)
- ✅ 527,918 daily weather summaries
- ✅ 1,593,482 synoptic observations
- ✅ API authentication working
- ✅ All endpoints tested and functional
- ✅ Swagger UI operational
- ✅ Historical queries working (1960s, 1980s, 2000s, 2020s)
- ✅ Database consistency verified

---

## Next Steps (Optional)

1. **Add More Stations**: If you get data for more stations, update the CSV and re-run import
2. **Set Up Production**: Deploy to a production server with proper security
3. **Add Rate Limiting**: Configure rate limits for production use
4. **Monitor Performance**: Set up logging and monitoring
5. **Backup Strategy**: Implement regular database backups

---

## Support

For issues or questions:
1. Check this documentation first
2. Run `python verify_station_count.py` to check database state
3. Check server logs for errors
4. Verify API key is correct

---

**Status**: ✅ FULLY OPERATIONAL
**Last Updated**: 2026-01-09
**API Key**: `2835b0ba074a0e24ba0e98f9d7046475`
