#!/usr/bin/env bash
# Production startup script for ExpenseFlow Pro backend
# Runs database migrations then starts the FastAPI server

set -euo pipefail

echo "=== ExpenseFlow Pro Backend Startup ==="
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Python path: $(which python)"

# Ensure we're in the backend directory
cd "$(dirname "$0")"

# Set PYTHONPATH to include the backend directory
export PYTHONPATH=.

echo "PYTHONPATH: $PYTHONPATH"

# Debug: Check if DATABASE_URL is set
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set!"
    echo "Available env vars (filtered):"
    env | grep -E '(DATABASE|POSTGRES|PG)' || echo "  No database-related env vars found"
    exit 1
else
    echo "DATABASE_URL is set (first 20 chars): ${DATABASE_URL:0:20}..."
fi

# Debug: Test Python imports
echo "Testing Python imports..."
python -c "
import sys
print('Python executable:', sys.executable)
print('Python path:', sys.path[:3])
try:
    from app.core.config import settings
    print('Settings imported successfully')
    print('DB URL (first 25 chars):', settings.DATABASE_URL[:25] + '...')
    print('Environment:', settings.ENVIRONMENT)
    print('Debug:', settings.DEBUG)
except Exception as e:
    print('ERROR importing settings:', e)
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

# Run database migrations with alembic
echo "Running database migrations (alembic upgrade head)..."
if ! alembic upgrade head; then
    echo "ERROR: Database migration failed!"
    echo "Alembic exit code: $?"
    exit 1
fi

echo "Database migrations completed successfully."

# Start the FastAPI server with uvicorn
echo "Starting FastAPI server on port ${PORT:-8080}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"