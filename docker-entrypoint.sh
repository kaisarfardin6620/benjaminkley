#!/bin/sh
# docker-entrypoint.sh

set -e
. /opt/venv/bin/activate

COMMAND=$1
echo "--- Received command: $COMMAND ---"

if [ "$COMMAND" = "web" ]; then
    echo "--- Running database migrations ---"
    python manage.py migrate --no-input

    echo "--- Collecting static files ---"
    python manage.py collectstatic --no-input --clear

    echo "--- Starting Gunicorn web server on port $PORT ---"
    exec gunicorn benjaminkley.wsgi --bind 0.0.0.0:$PORT --workers 3 --timeout 120

elif [ "$COMMAND" = "celery-worker" ]; then
    echo "--- Starting Celery worker ---"
    exec celery -A benjaminkley worker -l info

else
    echo "Unknown command: $COMMAND. Please use 'web' or 'celery-worker'."
    exit 1
fi