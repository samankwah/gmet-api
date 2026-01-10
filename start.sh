#!/bin/bash

# Production startup script for GMet Weather API

echo "Starting GMet Weather API..."

# Run database migrations
echo "Running database migrations..."
echo "Database URL: ${DATABASE_URL:-$SQLALCHEMY_DATABASE_URI}"
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
