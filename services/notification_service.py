"""Create in-app notifications and fan out push delivery.

Every Notification row in the app should be created through
create_notification so mobile devices get a matching push.
"""

from flask import current_app

from models import db, Notification


def create_notification(user_id, message, link):
    """Create a Notification row; enqueue a push best-effort."""
    notification = Notification(user_id=user_id, message=message, link=link)
    db.session.add(notification)
    db.session.commit()

    try:
        from services.push_service import apns_enabled
        if apns_enabled():
            from services.celery_tasks import send_push_task
            send_push_task.delay(user_id, message, link)
    except Exception as exc:
        # Push is best-effort: a down broker must never break the request.
        current_app.logger.warning(f'Push enqueue failed for user {user_id}: {exc}')

    return notification
