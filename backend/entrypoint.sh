#!/bin/sh
set -eu

echo "Applying WAZEN database migrations..."
alembic -c alembic.ini upgrade head

echo "Starting WAZEN API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
