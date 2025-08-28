#!/bin/sh
# docker-entrypoint.sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Activate the virtual environment
. /opt/venv/bin/activate

# Run database migrations
echo "--- Running database migrations ---"
python manage.py migrate --no-input

# Collect static files
echo "--- Collecting static files ---"
python manage.py collectstatic --no-input --clear

# Start the Gunicorn web server in the background
# It will listen on the port provided by the PORT environment variable.
echo "--- Starting Gunicorn web server on port $PORT ---"
gunicorn benjaminkley.wsgi --bind 0.0.0.0:$PORT &

# Start the Celery worker in the foreground
# This becomes the main process that keeps the container alive.
echo "--- Starting Celery worker ---"
celery -A benjaminkley worker -l info