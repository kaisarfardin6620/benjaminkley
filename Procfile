web: gunicorn benjaminkley.wsgi --workers 3 --timeout 30
worker: celery -A benjaminkley worker -l info