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
fi

echo "--- Ensuring correct permissions for scans output ---"
mkdir -p /app/scans/outputs
chown -R app:app /app/scans/outputs

# --- THIS IS THE FIX ---
# Use gosu to drop privileges and run the application as the 'app' user
if [ "$COMMAND" = "web" ]; then
    echo "--- Starting Gunicorn web server as user 'app' ---"
    exec gosu app gunicorn benjaminkley.wsgi --bind 0.0.0.0:$PORT --timeout 120 --workers 3

elif [ "$COMMAND" = "worker" ]; then
    echo "--- Starting Celry worker as user 'app' ---"
    exec gosu app celery -A benjaminkley worker -l info

elif [ "$COMMAND" = "beat" ]; then
    echo "--- Starting Celery beat scheduler as user 'app' ---"
    exec gosu app celery -A benjaminkley beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

else
    echo "Unknown command: $COMMAND. Please use 'web', 'worker', or 'beat'."
    exit 1
fi