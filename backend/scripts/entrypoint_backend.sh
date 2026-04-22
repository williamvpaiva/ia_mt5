#!/bin/bash

# Entrypoint script for backend container
# Runs database migrations and starts the FastAPI server

set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload