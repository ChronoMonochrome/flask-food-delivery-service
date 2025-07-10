#!/bin/sh
# entrypoint_web.sh

# This sets up a redirection for the *entire script* to output to stdout/stderr.
# All subsequent commands in this script will have their stdout/stderr redirected.
# This is usually the best approach for Docker containers.
exec >&2 # Redirect stdout to stderr so both go to Docker logs (common practice for entrypoints)
# Alternatively, to ensure everything goes to stdout (which Docker also captures):
# exec > /proc/1/fd/1 # Redirect stdout to /proc/1/fd/1 (Docker's stdout)
# exec 2>&1          # Redirect stderr to stdout

# Let's stick with the more common and often sufficient:
# All messages from `echo` commands will also go to Docker logs.

echo "Running Flask database migrations..."
export FLASK_APP=app
# Capture stderr from flask db upgrade explicitly if you want to see it in a log file.
# However, if you're already redirecting the whole script's output, this isn't strictly necessary.
# The '|| { ... }' block will also output to stderr if flask db upgrade fails.
flask db upgrade || { echo "Flask DB upgrade failed! Exiting."; exit 1; }


echo "Starting Gunicorn..."
# Gunicorn is configured to log to stdout/stderr already, which Docker captures.
# The 'exec' command replaces the current shell process with Gunicorn, ensuring Gunicorn's
# output becomes the primary output of the container.
exec gunicorn -w 4 -b 0.0.0.0:8011 --access-logfile - --error-logfile - app:app
