#!/bin/bash

# Production startup script for GMet Weather API

# Verify Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Warn if not using expected version
if [[ ! "$PYTHON_VERSION" =~ ^3\.11\. ]]; then
    echo "WARNING: Using Python $PYTHON_VERSION instead of expected 3.11.x"
    echo "SQLAlchemy 2.0.36+ supports Python 3.13, so this should work"
fi

echo "Starting GMet Weather API..."

# Run database migrations
echo "Running database migrations..."

# Display connection info for debugging (without exposing password)
if [ -n "$DATABASE_URL" ]; then
    echo "Using DATABASE_URL for migrations"
    # Strip password from URL for logging
    SAFE_URL=$(echo "$DATABASE_URL" | sed 's/:\/\/[^:]*:[^@]*@/:\/\/***:***@/')
    echo "Database URL: $SAFE_URL"
elif [ -n "$POSTGRES_SERVER" ]; then
    echo "Using individual Postgres environment variables"
    echo "Database: $POSTGRES_SERVER:${POSTGRES_PORT:-5432}/$POSTGRES_DB"
else
    echo "ERROR: No database configuration found!"
    echo "Missing both DATABASE_URL and POSTGRES_SERVER environment variables"
    exit 1
fi

alembic upgrade head

if [ $? -ne 0 ]; then
    echo "ERROR: Database migration failed. Aborting startup."
    exit 1
fi

echo "Database migrations completed successfully."

# Start the application with Gunicorn
echo "Starting Gunicorn server..."
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8000} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
