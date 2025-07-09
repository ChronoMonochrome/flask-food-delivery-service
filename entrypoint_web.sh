#!/bin/sh
# entrypoint_web.sh

echo "Waiting for database..."
# Using 'db' as the hostname for the database. When running with plain docker run,
# you'll need to ensure the containers are on the same network and aliased correctly.
# For a simple local test or if they are on the default bridge, 'db' might resolve.
# However, explicitly using the IP or linking might be necessary depending on your exact setup.
# For now, let's assume 'db' will be resolved if linked or on a shared network.
until nc -z db 3306; do
  echo "Database not ready yet, waiting..."
  sleep 2
done
echo "Database is ready."

echo "Running Flask database migrations..."
flask db upgrade

echo "Starting Gunicorn..."
exec gunicorn -w 4 -b 0.0.0.0:8011 --access-logfile - --error-logfile - app:app
