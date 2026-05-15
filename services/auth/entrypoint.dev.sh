#!/bin/sh
# =============================================================================
# entrypoint.dev.sh — Auth Service Development Entrypoint
# =============================================================================
# Make executable: chmod +x entrypoint.dev.sh
# =============================================================================

set -e

echo "⏳ Waiting for PostgreSQL..."
until pg_isready -h "${DB_HOST:-postgres}" -p "${DB_PORT:-5432}" -U "${DB_USER:-kraivor}"; do
    sleep 1
done
echo "✅ PostgreSQL is ready"

echo "⏳ Waiting for Redis..."
until redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping | grep -q PONG; do
    sleep 1
done
echo "✅ Redis is ready"

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "🚀 Starting development server..."
exec python manage.py runserver 0.0.0.0:8001