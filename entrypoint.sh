#!/bin/sh
set -eu
echo "Running migrations..."
python manage.py migrate --noinput
echo "Starting gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-2}" --threads "${GUNICORN_THREADS:-4}" --timeout 120
