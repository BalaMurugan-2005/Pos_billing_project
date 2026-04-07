#!/bin/bash

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Seed demo users
echo "Seeding demo users..."
python manage.py seed_demo_users

# Start gunicorn
echo "Starting Gunicorn..."
gunicorn pos_system.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
