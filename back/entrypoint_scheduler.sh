#!/bin/sh
# entrypoint_scheduler.sh

echo "Waiting for web service (and migrations to complete)..."
# Assuming 'web' is the hostname for the web service.
until nc -z bot_mandarin_web 8011; do
  echo "Web service not ready yet, waiting..."
  sleep 2
done
echo "Web service is ready."

echo "Starting scheduler..."
exec python scheduler.py
