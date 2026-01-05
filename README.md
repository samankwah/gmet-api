# GMet Weather Data API

A RESTful Weather Data API for the Ghana Meteorological Agency (GMet) built with FastAPI, PostgreSQL, and modern Python practices.

## Features

- **FastAPI Framework**: High-performance async API with automatic OpenAPI documentation
- **PostgreSQL Database**: Robust data storage with SQLAlchemy ORM
- **API Key Authentication**: Secure access control with API keys
- **Weather Data Management**: Current weather, forecasts, and historical data
- **Docker Support**: Containerized deployment with Docker Compose
- **Database Migrations**: Alembic for schema versioning
- **Production Ready**: CORS, rate limiting, logging, and error handling

## Project Structure

```
gmet-weather-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application instance
│   ├── config.py            # Pydantic settings configuration
│   ├── database.py          # SQLAlchemy database setup
│   ├── models/              # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── base.py          # Base model with common fields
│   │   └── weather_data.py  # Weather-related models
│   ├── schemas/             # Pydantic schemas for requests/responses
│   │   ├── __init__.py
│   │   ├── base.py          # Base schemas
│   │   ├── auth.py          # Authentication schemas
│   │   └── weather.py       # Weather data schemas
│   ├── crud/                # CRUD operations
│   │   ├── __init__.py
│   │   ├── base.py          # Base CRUD operations
│   │   ├── user.py          # User CRUD
│   │   └── weather.py       # Weather data CRUD
│   ├── routers/             # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication endpoints
│   │   └── weather.py       # Weather data endpoints
│   ├── dependencies/        # Dependency injection
│   │   ├── __init__.py
│   │   └── auth.py          # Authentication dependencies
│   └── utils/               # Utility functions
│       ├── __init__.py
│       └── security.py      # Security utilities
├── alembic/                 # Database migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── tests/                   # Unit and integration tests
│   ├── __init__.py
│   └── test_main.py
├── .env.example             # Environment variables template
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
└── alembic.ini
```

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional, but recommended)

## Quick Start with Docker (Recommended)

1. **Clone the repository** (if applicable) and navigate to the project directory

2. **Start the services:**

   ```bash
   docker-compose up -d
   ```

3. **Run database migrations:**

   ```bash
   docker-compose exec api alembic upgrade head
   ```

4. **Access the API:**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Alternative Docs: http://localhost:8000/redoc

## Manual Setup (Without Docker)

### 1. Clone and Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup PostgreSQL Database

```bash
# Create database
createdb gmet_weather

# Or using psql
psql -c "CREATE DATABASE gmet_weather;"
psql -c "CREATE USER gmet_user WITH PASSWORD 'gmet_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE gmet_weather TO gmet_user;"
```

### 3. Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 4. Run Database Migrations

```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations (creates all tables including api_keys)
alembic upgrade head
```

### 5. Create Your First API Key

After running migrations, create your first API key:

**Option A: Using the API endpoint**
```bash
curl -X POST "http://localhost:8000/api/v1/api-keys/" \
  -H "Content-Type: application/json" \
  -d '{"name": "Development Key", "role": "read_only"}'
```

**Option B: Using the seed script**
```bash
python -m scripts.seed_api_keys
```

⚠️ **Store the returned API key securely** - it will not be shown again!

### 6. Start the Application

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

| Variable                      | Description                    | Default                 |
| ----------------------------- | ------------------------------ | ----------------------- |
| `DEBUG`                       | Enable debug mode              | `True`                  |
| `SECRET_KEY`                  | JWT secret key                 | Auto-generated          |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time          | `60`                    |
| `POSTGRES_SERVER`             | PostgreSQL host                | `localhost`             |
| `POSTGRES_USER`               | PostgreSQL username            | `gmet_user`             |
| `POSTGRES_PASSWORD`           | PostgreSQL password            | `gmet_password`         |
| `POSTGRES_DB`                 | PostgreSQL database name       | `gmet_weather`          |
| `POSTGRES_PORT`               | PostgreSQL port                | `5432`                  |
| `BACKEND_CORS_ORIGINS`        | CORS allowed origins           | `http://localhost:3000` |
| `RATE_LIMIT_REQUESTS`         | Rate limit requests per window | `100`                   |
| `RATE_LIMIT_WINDOW`           | Rate limit window in seconds   | `60`                    |

## API Endpoints

### Authentication & API Keys

- `POST /api/v1/api-keys/` - Create a new API key
- `GET /api/v1/api-keys/` - List all API keys (masked)
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/apikey/regenerate` - Regenerate API key

### Weather Data

- `GET /api/v1/weather/stations` - List weather stations
- `GET /api/v1/weather/current/{station_code}` - Get current weather
- `GET /api/v1/weather/forecast/{station_code}` - Get weather forecast
- `GET /api/v1/weather/history/{station_code}` - Get historical weather
- `GET /api/v1/weather/stations/{station_code}` - Get station details

### Health Check

- `GET /` - API root endpoint
- `GET /health` - Health check

## Authentication

The API uses **API key authentication** to secure access to all endpoints (except `/health` and `/`).

### Getting Your API Key

#### Option 1: Create via API Endpoint (Recommended)

After running database migrations, create your first API key using the management endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/api-keys/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Application",
    "role": "read_only"
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "My Application",
  "role": "read_only",
  "key": "abc123def456...",
  "message": "Store this key securely – it will not be shown again!"
}
```

⚠️ **IMPORTANT**: The plain text API key is shown **only once** in the response. Store it securely immediately!

#### Option 2: Run Seed Script (Development Only)

For development, you can generate a default development key:

```bash
python -m scripts.seed_api_keys
```

This creates a key named "Development Key" and prints the plain text key to the console.

### Using Your API Key

Include your API key in the `X-API-Key` header for all authenticated requests:

```bash
curl -H "X-API-Key: your-api-key-here" \
  http://localhost:8000/api/v1/weather/stations
```

### API Key Management

**Endpoints:**
- `POST /api/v1/api-keys/` - Create a new API key (currently open, will be secured in next phase)
- `GET /api/v1/api-keys/` - List all API keys (masked, no sensitive data)

**Key Roles:**
- `read_only` - Read-only access to weather data
- `admin` - Full access (future: admin operations)
- `partner` - Partner-level access (future: extended features)

**Key Properties:**
- Keys are **hashed using bcrypt** before storage
- Each key has a descriptive `name` for easy identification
- Keys can be **activated/deactivated** without deletion
- Last usage timestamp (`last_used_at`) is tracked automatically

### Security Best Practices

1. **Store keys securely**: Never commit API keys to version control
2. **Use environment variables**: Store keys in `.env` files or secure key management systems
3. **Rotate keys regularly**: Create new keys and revoke old ones periodically
4. **Use appropriate roles**: Assign the minimum required role (`read_only` when possible)
5. **Monitor usage**: Check `last_used_at` timestamps to detect unused or compromised keys

### Public Endpoints

The following endpoints **do not require authentication**:
- `GET /` - API root/info
- `GET /health` - Health check

All other endpoints (including `/api/v1/*` and `/v1/*`) require a valid API key.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
```

### Database Operations

```bash
# Create new migration
alembic revision --autogenerate -m "Migration message"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f api

# Execute commands in container
docker-compose exec api bash

# Rebuild and restart
docker-compose up -d --build
```

## Data Model – GMet Synoptic Schedule

The GMet Weather API database model reflects the operational practices of the Ghana Meteorological Agency:

### Synoptic Observations

Automatic weather stations transmit observations at **fixed times**: **0600, 0900, 1200, and 1500 UTC** (Ghana time). These match the standard **SYNOP reporting schedule** used by meteorological agencies worldwide.

At each observation time, the system captures:

- **Instantaneous temperature** (°C)
- **Relative humidity** (%)
- **Wind speed** (m/s) and **wind direction** (degrees, 0-360)
- **Station pressure** (hPa)
- **Rainfall** (mm since last observation, typically 3-hourly accumulation)

The `synoptic_observations` table stores these instantaneous measurements with:

- Unique constraint on `(station_id, obs_datetime)` to prevent duplicates
- Indexes optimized for time-series queries
- Timezone-aware timestamps for accurate temporal analysis

**Note**: Future implementations can add a validator to ensure `obs_datetime.hour` is in `[6, 9, 12, 15]` to enforce the SYNOP schedule.

### Daily Summaries

The `daily_summaries` table aggregates synoptic observations into daily statistics used in:

- **Public weather bulletins**
- **Climatological reports**
- **Historical analysis**

Daily summaries are calculated over a **24-hour period** (typically from 0600 UTC to 0600 UTC the next day) and include:

- **Maximum and minimum temperatures** with timestamps
- **Total 24-hour rainfall**
- **Mean relative humidity** (average of 0600, 0900, 1200, 1500 observations)
- **Maximum wind gust**

This structure supports both:

- **Real-time monitoring** via synoptic observations
- **Official reporting** via daily summaries

### Data Flow

1. **Automatic weather stations** transmit data at 0600, 0900, 1200, 1500 UTC
2. **Synoptic observations** are stored immediately in `synoptic_observations`
3. **Daily summaries** are calculated and stored in `daily_summaries` (typically after 0600 UTC the next day)

## Database Schema

### API Keys Table

- `id`: Primary key
- `key`: Hashed API key (bcrypt, 64 chars, unique, indexed)
- `name`: Descriptive name (e.g., "Internal Dashboard", "Mobile App")
- `role`: Key role (`admin`, `read_only`, `partner`)
- `is_active`: Whether the key is active (default: `True`)
- `last_used_at`: Timestamp of last usage (nullable)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- **Indexes**: Unique on `key`, index on `is_active`

### Users Table

- `id`: Primary key
- `email`: Unique email address
- `hashed_password`: Password hash
- `is_active`: Account status
- `is_superuser`: Admin privileges
- `api_key`: Unique API key (legacy, use APIKey model for new keys)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Stations Table

- `id`: Primary key
- `name`: Station name
- `code`: Unique station code (e.g., DGAA for Kotoka International Airport)
- `latitude`: Latitude in degrees
- `longitude`: Longitude in degrees
- `region`: Region or administrative area
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Synoptic Observations Table

- `id`: Primary key
- `station_id`: Foreign key to stations
- `obs_datetime`: Exact observation time (timezone-aware)
- `temperature`: Instantaneous air temperature (°C)
- `relative_humidity`: Relative humidity (%)
- `wind_speed`: Wind speed (m/s)
- `wind_direction`: Wind direction (degrees, 0-360)
- `pressure`: Station pressure (hPa)
- `rainfall`: Rainfall since last observation (mm)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- **Unique constraint**: `(station_id, obs_datetime)`

### Daily Summaries Table

- `id`: Primary key
- `station_id`: Foreign key to stations
- `date`: Observation date
- `temp_max`: Maximum temperature (°C)
- `temp_max_time`: Time when maximum temperature was recorded
- `temp_min`: Minimum temperature (°C)
- `temp_min_time`: Time when minimum temperature was recorded
- `rainfall_total`: Total 24-hour rainfall (mm)
- `mean_rh`: Mean relative humidity (%)
- `max_wind_gust`: Maximum wind gust (m/s)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- **Unique constraint**: `(station_id, date)`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or issues, please open an issue on the GitHub repository or contact the development team.
