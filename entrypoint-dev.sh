#!/bin/sh

# Apply database migrations
echo "Applying database migrations..."
python manage.py makemigrations
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
# python manage.py collectstatic --noinput

# Start development server
echo "Starting development server..."
python manage.py runserver 0.0.0.0:8000