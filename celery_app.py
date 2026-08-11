"""Celery application configuration for background tasks."""

import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def make_celery():
    """Create and configure Celery application."""
    env = os.getenv('FLASK_ENV', 'development')
    is_prod = env == 'production'

    if is_prod:
        # Production: Redis broker + result backend.
        broker_url = os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        # Handle Heroku Redis SSL
        if broker_url.startswith('rediss://'):
            broker_url += '?ssl_cert_reqs=none'
        backend = broker_url
        extra_conf = {}
    else:
        # Dev/test: no local Redis on developer machines. An in-memory
        # transport never fails, so Celery no longer retries an unreachable
        # external backend until its retry limit — which surfaced as a fatal
        # (Sentry-paged) 'Retry limit exceeded ... result store backend' while
        # running the dev/test suite without redis running.
        broker_url = 'memory://'
        backend = None
        extra_conf = {'task_ignore_result': True}

    celery = Celery(
        'wishlist',
        broker=broker_url,
        backend=backend,
        include=['services.celery_tasks']
    )

    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minute timeout for small tasks
        worker_prefetch_multiplier=1,  # One task at a time
        broker_connection_retry_on_startup=True,
        **extra_conf,
        # @spec AUTO-TSK-010
        beat_schedule={
            # Refresh prices for items older than the 7-day staleness window.
            # Every 6 hours: a stale item is refreshed within 6h of crossing
            # the window; runs with nothing stale are near-free (query-only).
            'update-stale-prices': {
                'task': 'services.celery_tasks.update_stale_prices_async',
                'schedule': crontab(minute=0, hour='*/6'),
            },
        },
    )
    
    return celery

celery_app = make_celery()
