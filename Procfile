web: gunicorn app:app
worker: celery -A celery_app worker --loglevel=info
# release: flask db upgrade  # Temporarily disabled - migration mismatch