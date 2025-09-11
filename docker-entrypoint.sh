#!/bin/sh
# docker-entrypoint.sh

set -e
. /opt/venv/bin/activate

chown -R app:app /app/media /app/staticfiles /app/scans

COMMAND=$1
echo "--- Received command: $COMMAND ---"

if [ "$COMMAND" = "web" ]; then
    echo "--- Running database migrations ---"
    python manage.py migrate --no-input

    echo "--- Collecting static files ---"
    python manage.py collectstatic --no-input --clear
fi

if [ "$COMMAND" = "web" ]; then
    echo "--- Starting Gunicorn web server on port $PORT ---"
    exec gunicorn benjaminkley.wsgi --bind 0.0.0.0:$PORT --workers 3 --timeout 120

elif [ "$COMMAND" = "worker" ]; then
    echo "--- Starting Celery worker ---"
    exec celery -A benjaminkley worker -l info

elif [ "$COMMAND" = "beat" ]; then
    echo "--- Starting Celery beat scheduler ---"
    exec celery -A benjaminkley beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

else
    echo "Unknown command: $COMMAND. Please use 'web', 'worker', or 'beat'."
    exit 1
fi