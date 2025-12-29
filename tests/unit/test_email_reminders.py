"""Tests for the email reminder functionality."""
import datetime
from unittest.mock import patch, MagicMock
import pytest
from app import db, User, Event, Item


@pytest.fixture
def claimer(app):
    """Create a user who will claim items."""
    with app.app_context():
        user = User(name="Claimer", email="claimer@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def recipient(app):
    """Create a user whose items will be claimed."""
    with app.app_context():
        user = User(name="Recipient", email="recipient@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def event_creator(app):
    """Create a user who will create events."""
    with app.app_context():
        user = User(name="Creator", email="creator@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


class TestEventReminderTask:
    """Tests for the send_event_reminders task."""

    def test_task_module_exists(self, app):
        """Task module should be importable."""
        from tasks import send_event_reminders
        assert callable(send_event_reminders)

    def test_finds_events_seven_days_out(self, app, event_creator):
        """Task should find events that are exactly 7 days away."""
        from tasks import send_event_reminders

        # Setup: create events within app context
        with app.app_context():
            today = datetime.date.today()

            # Create events at different distances
            event_7_days = Event(
                name="7 Days Away",
                date=today + datetime.timedelta(days=7),
                created_by_id=event_creator,
                reminder_sent=False
            )
            event_6_days = Event(
                name="6 Days Away",
                date=today + datetime.timedelta(days=6),
                created_by_id=event_creator,
                reminder_sent=False
            )
            event_8_days = Event(
                name="8 Days Away",
                date=today + datetime.timedelta(days=8),
                created_by_id=event_creator,
                reminder_sent=False
            )
            db.session.add_all([event_7_days, event_6_days, event_8_days])
            db.session.commit()

        # Run the task with mocking
        with patch('email_service.send_event_reminder') as mock_send:
            mock_send.return_value = True
            stats = send_event_reminders(app, db, Event, Item, User)

            # Only the 7-day event should be processed
            assert stats['events_processed'] == 1

    def test_skips_already_sent_reminders(self, app, event_creator):
        """Task should skip events that already had reminders sent."""
        from tasks import send_event_reminders

        with app.app_context():
            today = datetime.date.today()

            event = Event(
                name="Already Sent",
                date=today + datetime.timedelta(days=7),
                created_by_id=event_creator,
                reminder_sent=True  # Already sent
            )
            db.session.add(event)
            db.session.commit()

        with patch('email_service.send_event_reminder') as mock_send:
            stats = send_event_reminders(app, db, Event, Item, User)

            # Should not process any events
            assert stats['events_processed'] == 0
            mock_send.assert_not_called()

    def test_handles_no_claimed_items(self, app, event_creator):
        """Task should handle events with no claimed items gracefully."""
        from tasks import send_event_reminders

        with app.app_context():
            today = datetime.date.today()

            event = Event(
                name="Empty Event",
                date=today + datetime.timedelta(days=7),
                created_by_id=event_creator,
                reminder_sent=False
            )
            db.session.add(event)
            db.session.commit()

        with patch('email_service.send_event_reminder') as mock_send:
            stats = send_event_reminders(app, db, Event, Item, User)

            # Should process the event but send no emails
            assert stats['events_processed'] == 1
            assert stats['emails_sent'] == 0
            mock_send.assert_not_called()


class TestEmailService:
    """Tests for the email service module."""

    def test_email_service_module_exists(self, app):
        """Email service module should be importable."""
        from email_service import send_event_reminder, send_email
        assert callable(send_event_reminder)
        assert callable(send_email)


class TestSendRemindersCommand:
    """Tests for the flask send-reminders CLI command."""

    def test_command_exists(self, app):
        """CLI command should be registered."""
        # Verify the command is registered
        from app import app as flask_app
        assert 'send-reminders' in [cmd.name for cmd in flask_app.cli.commands.values()]
