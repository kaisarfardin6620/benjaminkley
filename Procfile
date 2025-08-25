web: gunicorn benjaminkley.wsgi --workers 3 --timeout 30
worker: pip install -r requirements.txt && celery -A benjaminkley worker -l info