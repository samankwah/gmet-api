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

# Apply migrations
alembic upgrade head
```

### 5. Start the Application

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `True` |
| `SECRET_KEY` | JWT secret key | Auto-generated |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time | `60` |
| `POSTGRES_SERVER` | PostgreSQL host | `localhost` |
| `POSTGRES_USER` | PostgreSQL username | `gmet_user` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `gmet_password` |
| `POSTGRES_DB` | PostgreSQL database name | `gmet_weather` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `BACKEND_CORS_ORIGINS` | CORS allowed origins | `http://localhost:3000` |
| `RATE_LIMIT_REQUESTS` | Rate limit requests per window | `100` |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds | `60` |

## API Endpoints

### Authentication
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

The API uses API key authentication. Include your API key in the request header:

```
Authorization: Bearer your-api-key-here
```

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

## Database Schema

### Users Table
- `id`: Primary key
- `email`: Unique email address
- `hashed_password`: Password hash
- `is_active`: Account status
- `is_superuser`: Admin privileges
- `api_key`: Unique API key
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Weather Stations Table
- `id`: Primary key
- `name`: Station name
- `code`: Unique station code
- `location`: Geographic location
- `latitude/longitude`: GPS coordinates
- `elevation`: Height above sea level
- `is_active`: Station status

### Weather Readings Table
- `id`: Primary key
- `station_id`: Foreign key to stations
- `reading_type`: current/forecast/historical
- Weather measurements (temperature, humidity, pressure, etc.)
- `reading_timestamp`: When data was recorded

### Forecast Data Table
- Similar to readings but for forecast data
- `forecast_timestamp`: When forecast is for
- `forecast_model`: Model used for prediction
- `forecast_horizon`: Hours ahead

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
