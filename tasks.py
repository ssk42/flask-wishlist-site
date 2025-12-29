"""Background tasks for the Wishlist application."""
import datetime
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def send_event_reminders(app, db, Event, Item, User):
    """Send reminder emails for events happening in 7 days.

    This function:
    1. Finds events where date is exactly 7 days from now and reminder_sent is False
    2. For each event, finds all users who have claimed items for that event
    3. Sends each user an email listing their claimed items with links
    4. Marks reminder_sent = True on the event

    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
        Event: Event model class
        Item: Item model class
        User: User model class

    Returns:
        Dictionary with counts of events processed, emails sent, and errors
    """
    from email_service import send_event_reminder

    with app.app_context():
        today = datetime.date.today()
        reminder_date = today + datetime.timedelta(days=7)

        # Find events happening in exactly 7 days that haven't had reminders sent
        events = Event.query.filter(
            Event.date == reminder_date,
            Event.reminder_sent == False  # noqa: E712
        ).all()

        stats = {
            'events_processed': 0,
            'emails_sent': 0,
            'errors': 0
        }

        for event in events:
            logger.info(f'Processing event: {event.name} (id={event.id})')

            # Find all claimed items for this event (grouped by claimer)
            claimed_items = Item.query.filter(
                Item.event_id == event.id,
                Item.status.in_(['Claimed', 'Purchased']),
                Item.last_updated_by_id.isnot(None)
            ).all()

            if not claimed_items:
                logger.info(f'No claimed items for event {event.name}, marking as processed')
                event.reminder_sent = True
                db.session.commit()
                stats['events_processed'] += 1
                continue

            # Group items by the user who claimed them
            user_items = defaultdict(list)
            for item in claimed_items:
                if item.last_updated_by_id and item.user_id != item.last_updated_by_id:
                    user_items[item.last_updated_by_id].append(item)

            # Send reminder to each user who has claimed items
            for claimer_id, items in user_items.items():
                claimer = db.session.get(User, claimer_id)
                if not claimer:
                    continue

                # Prepare item list for the email
                item_list = []
                for item in items:
                    item_info = {
                        'description': item.description,
                        'recipient_name': item.user.name,
                        'price': item.price,
                        'link': item.link,
                        'status': item.status
                    }
                    item_list.append(item_info)

                try:
                    success = send_event_reminder(
                        user_email=claimer.email,
                        user_name=claimer.name,
                        event_name=event.name,
                        event_date=event.date,
                        claimed_items=item_list
                    )
                    if success:
                        stats['emails_sent'] += 1
                        logger.info(f'Sent reminder to {claimer.email} for event {event.name}')
                    else:
                        stats['errors'] += 1
                except Exception as e:
                    logger.error(f'Failed to send reminder to {claimer.email}: {str(e)}')
                    stats['errors'] += 1

            # Mark the event as having had its reminder sent
            event.reminder_sent = True
            db.session.commit()
            stats['events_processed'] += 1

        logger.info(f'Event reminders complete: {stats}')
        return stats
