#!/bin/sh
# docker-entrypoint.sh (FINAL, FLEXIBLE VERSION)

# Exit immediately if a command exits with a non-zero status.
set -e

# Activate the virtual environment
. /opt/venv/bin/activate

# This is the "argument" passed to the script from compose.yaml
# It will be 'web', 'worker', or 'beat'.
COMMAND=$1

echo "--- Received command: $COMMAND ---"

# --- Run shared setup tasks ONLY on the 'web' process ---
# This prevents workers from trying to run migrations at the same time.
if [ "$COMMAND" = "web" ]; then
    echo "--- Running database migrations ---"
    python manage.py migrate --no-input

    echo "--- Collecting static files ---"
    python manage.py collectstatic --no-input --clear
fi

# --- Execute the specific command for this container ---
# The 'exec' command replaces the shell process with the application process,
# which is a Docker best practice for signal handling.

if [ "$COMMAND" = "web" ]; then
    echo "--- Starting Gunicorn web server on port $PORT ---"
    exec gunicorn benjaminkley.wsgi --bind 0.0.0.0:$PORT --timeout 120 --workers 3

elif [ "$COMMAND" = "worker" ]; then
    echo "--- Starting Celery worker ---"
    exec celery -A benjaminkley worker -l info

elif [ "$COMMAND" = "beat" ]; then
    echo "--- Starting Celery beat scheduler ---"
    # Note: Requires django-celery-beat to be installed
    exec celery -A benjaminkley beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

else
    echo "Unknown command: $COMMAND. Please use 'web', 'worker', or 'beat'."
    exit 1
fi