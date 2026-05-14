#!/bin/bash
set -e
echo "Running Django migrations..."
python manage.py migrate --noinput
echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "Creating superuser if none exists..."
python manage.py create_superuser_if_none
echo "Starting Django..."
exec python manage.py runserver 0.0.0.0:8080
