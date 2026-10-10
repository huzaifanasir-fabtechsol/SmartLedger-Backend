#!/bin/sh
set -e

echo "Waiting for PostgreSQL to be ready on ${POSTGRES_HOST}:${POSTGRES_PORT}..."
while ! nc -z ${POSTGRES_HOST:-127.0.0.1} ${POSTGRES_PORT:-5433}; do
  sleep 0.5
done
echo "PostgreSQL is ready!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || true

echo "Starting Gunicorn server on 127.0.0.1:${WEB_PORT:-8007}..."
exec gunicorn project.wsgi:application \
    --bind 127.0.0.1:${WEB_PORT:-8007} \
    --workers 3 \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
