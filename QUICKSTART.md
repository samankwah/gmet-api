# GMet Weather API - Quick Start Guide

Get the GMet Weather API up and running in **5 minutes**!

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git (optional)

## 🚀 Quick Start

### Option 1: Docker (Recommended - 3 minutes)

```bash
# 1. Navigate to project directory
cd met-api

# 2. Start all services (API + PostgreSQL + Redis)
docker-compose up -d

# 3. Check services are running
docker-compose ps

# 4. Run database migrations
docker-compose exec api alembic upgrade head

# 5. Seed Ghana weather stations
docker-compose exec api python -m scripts.seed_ghana_stations

# 6. Done! API is running at http://localhost:8000
```

**Access the API:**
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Option 2: Local Development (5 minutes)

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env if needed

# 5. Run migrations
alembic upgrade head

# 6. Seed Ghana weather stations
python -m scripts.seed_ghana_stations

# 7. Start the server
uvicorn app.main:app --reload

# 8. Done! API is running at http://localhost:8000
```

## 📝 First Steps

### 1. Register a User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@gmet.gov.gh",
    "password": "securepassword123",
    "is_active": true,
    "is_superuser": false
  }'
```

**Response:**
```json
{
  "user_id": 1,
  "email": "testuser@gmet.gov.gh",
  "api_key": "abc123xyz789...",
  "is_active": true,
  "created_at": "2026-01-03T12:00:00Z"
}
```

**Save your API key!** You'll need it for all requests.

### 2. Get Current Weather for Accra

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "http://localhost:8000/v1/current?location=Accra"
```

**Response:**
```json
{
  "id": 1,
  "station_id": 1,
  "timestamp": "2026-01-03T14:30:00Z",
  "temperature": 28.5,
  "humidity": 75.0,
  "wind_speed": 12.5,
  "wind_direction": 180.0,
  "rainfall": 0.0,
  "pressure": 1013.25
}
```

### 3. Get Historical Data

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "http://localhost:8000/v1/historical?station=Kumasi&start=2025-01-01&end=2025-01-31"
```

### 4. List All Stations

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "http://localhost:8000/api/v1/weather/stations"
```

### 5. Filter Stations by Region

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "http://localhost:8000/api/v1/weather/stations?region=Ashanti"
```

## 🧪 Test the API

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_auth.py
```

### Interactive API Documentation

Visit **http://localhost:8000/docs** for interactive Swagger documentation where you can:
- See all endpoints
- Try requests directly in the browser
- View request/response schemas
- Test authentication

## 📍 Available Locations

Query these cities by name:

**Major Cities:**
- Accra (DGAA)
- Kumasi (DGSI)
- Tamale (DGLE)
- Takoradi (DGTK)
- Cape Coast (DGCC)
- Koforidua (DGKF)
- Ho (DGHO)
- Bolgatanga (DGBG)
- Wa (DGWA)
- Sunyani (DGSN)

**More Stations:**
- Tema (DGTM)
- Saltpond (DGSP)
- Yendi (DGYN)
- Wenchi (DGWN)
- Navrongo (DGNV)

## 🔧 Common Commands

### Check Service Status
```bash
docker-compose ps
```

### View Logs
```bash
# All services
docker-compose logs -f

# API only
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

### Restart Services
```bash
docker-compose restart
```

### Stop Services
```bash
docker-compose down
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Database Operations
```bash
# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec api alembic upgrade head

# Rollback migration
docker-compose exec api alembic downgrade -1

# View migration history
docker-compose exec api alembic history
```

### Access Database
```bash
# PostgreSQL
docker-compose exec db psql -U gmet_user -d gmet_weather

# Redis
docker-compose exec redis redis-cli
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

### Database Connection Error
```bash
# Wait for database to be ready
docker-compose exec db pg_isready -U gmet_user

# Check database logs
docker-compose logs db
```

### Redis Not Available
Redis caching is optional. The API will work without it:
```bash
# Check Redis status
docker-compose exec redis redis-cli ping
# Should return: PONG
```

### Migration Errors
```bash
# Reset database (WARNING: destroys data)
docker-compose down -v
docker-compose up -d
docker-compose exec api alembic upgrade head
```

## 📚 Next Steps

1. **Read the API Documentation:** http://localhost:8000/docs
2. **Review Implementation Summary:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
3. **Check Project Design Document:** See PDR for full specifications
4. **Run Tests:** `pytest` to ensure everything works
5. **Add Test Data:** Create observations for testing

## 💡 Tips

- Use **Swagger UI** (http://localhost:8000/docs) for testing - it's interactive!
- **Save your API key** from registration - you can't retrieve it later
- Check **logs/** directory for application logs
- Use **rate limit headers** in responses to track usage
- Enable **DEBUG=False** in production

## 🆘 Getting Help

- **API Documentation:** http://localhost:8000/docs
- **Logs:** `docker-compose logs -f api`
- **Health Check:** http://localhost:8000/health
- **Cache Health:** Call Redis health_check() function

## 🎯 Sample Workflow

```bash
# 1. Register
API_KEY=$(curl -s -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@gmet.gh","password":"demo123","is_active":true,"is_superuser":false}' \
  | jq -r '.api_key')

echo "Your API Key: $API_KEY"

# 2. Get current weather
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/v1/current?location=Accra" | jq '.'

# 3. Get all stations
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/api/v1/weather/stations" | jq '.'

# 4. Add an observation (requires station_id from step 3)
curl -X POST "http://localhost:8000/api/v1/weather/observations" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": 1,
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "temperature": 28.5,
    "humidity": 75.0,
    "wind_speed": 10.0,
    "rainfall": 0.0,
    "pressure": 1013.0
  }' | jq '.'

# 5. Get latest observation
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/api/v1/weather/stations/DGAA/latest" | jq '.'
```

---

**You're all set!** 🎉

The GMet Weather API is now running and ready to serve weather data for Ghana.

For detailed information, see the full documentation at http://localhost:8000/docs
