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

# --- START OF THE FIX ---
# We are now hardcoding the port to 8080, which is the standard
# port that Railway's gateway will try to connect to.
echo "--- Starting Gunicorn web server on port 8080 ---"
gunicorn benjaminkley.wsgi --bind 0.0.0.0:8080 &
# --- END OF THE FIX ---

# Start the Celery worker in the foreground
# This becomes the main process that keeps the container alive.
echo "--- Starting Celery worker ---"
celery -A benjaminkley worker -l info