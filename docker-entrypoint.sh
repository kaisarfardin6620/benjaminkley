
#!/bin/sh
set -e

# Activate venv
. /opt/venv/bin/activate

# Run migrations
python manage.py migrate --no-input

# Collect static files
python manage.py collectstatic --no-input --clear

# Start Gunicorn
exec gunicorn benjaminkley.wsgi --bind 0.0.0.0:8000 --timeout 120 --workers 2 --max-requests 1000