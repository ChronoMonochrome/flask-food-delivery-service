#!/bin/sh
# entrypoint_web.sh

echo "Running Flask database migrations..."
flask db upgrade

echo "Starting Gunicorn..."
exec gunicorn -w 4 -b 0.0.0.0:8011 --access-logfile - --error-logfile - app:app
