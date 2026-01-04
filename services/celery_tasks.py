"""Celery tasks for background processing.

These tasks wrap the existing task logic from services/tasks.py for async execution.
"""
import logging
from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_event_reminders_async(self):
    """Celery task: Send reminder emails for events happening in 7 days.
    
    This task requires the Flask app context to access the database.
    It imports and calls the existing send_event_reminders function.
    """
    from app import create_app
    from models import db, Event, Item, User
    from services.tasks import send_event_reminders
    
    try:
        app = create_app()
        result = send_event_reminders(app, db, Event, Item, User)
        logger.info(f'send_event_reminders completed: {result}')
        return result
    except Exception as exc:
        logger.error(f'send_event_reminders failed: {exc}')
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def update_stale_prices_async(self, force_all=False):
    """Celery task: Update prices for items that haven't been checked recently.
    
    Args:
        force_all: If True, update all items regardless of last update time
    """
    from app import create_app
    from models import db, Item, Notification
    from services.price_service import update_stale_prices
    
    try:
        app = create_app()
        result = update_stale_prices(app, db, Item, Notification, force_all=force_all)
        logger.info(f'update_stale_prices completed: {result}')
        return result
    except Exception as exc:
        logger.error(f'update_stale_prices failed: {exc}')
        raise self.retry(exc=exc, countdown=60)
