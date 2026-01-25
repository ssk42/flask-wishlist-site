"""Celery application configuration for background tasks."""

import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def make_celery():
    """Create and configure Celery application."""
    # Get broker URL from environment (Redis)
    broker_url = os.getenv('CELERY_BROKER_URL') or os.getenv(
        'REDIS_URL', 'redis://localhost:6379/0')

    # Handle Heroku Redis SSL
    if broker_url.startswith('rediss://'):
        broker_url += '?ssl_cert_reqs=none'

    celery = Celery(
        'wishlist',
        broker=broker_url,
        backend=broker_url,
        include=['services.celery_tasks']
    )

    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minute timeout
        worker_prefetch_multiplier=1,  # One task at a time
    )

    return celery


celery_app = make_celery()
