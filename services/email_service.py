"""Email service for sending notifications."""
import logging
from flask import current_app, render_template
from flask_mail import Mail, Message

mail = Mail()

logger = logging.getLogger(__name__)


def init_mail(app):
    """Initialize Flask-Mail with the app."""
    mail.init_app(app)


def send_email(to, subject, template_name, **kwargs):
    """Send an email using the specified template.

    Args:
        to: Email recipient address
        subject: Email subject line
        template_name: Name of the template (without extension)
        **kwargs: Context variables for the template

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            sender=current_app.config.get(
                'MAIL_DEFAULT_SENDER',
                'noreply@wishlist.app'))

        # Render both HTML and plain text versions
        msg.html = render_template(f'email/{template_name}.html', **kwargs)
        msg.body = render_template(f'email/{template_name}.txt', **kwargs)

        mail.send(msg)
        logger.info(f'Email sent successfully to {to}: {subject}')
        return True
    except Exception as e:
        logger.error(f'Failed to send email to {to}: {str(e)}', exc_info=True)
        return False


def send_event_reminder(
        user_email,
        user_name,
        event_name,
        event_date,
        claimed_items):
    """Send a reminder email about claimed items for an upcoming event.

    Args:
        user_email: Recipient email address
        user_name: Recipient's name
        event_name: Name of the event
        event_date: Date of the event
        claimed_items: List of items the user has claimed for this event

    Returns:
        True if email was sent successfully, False otherwise
    """
    return send_email(
        to=user_email,
        subject=f'Reminder: {event_name} is coming up in 7 days!',
        template_name='event_reminder',
        user_name=user_name,
        event_name=event_name,
        event_date=event_date,
        claimed_items=claimed_items
    )
