"""Tests for background tasks with mocked dependencies."""
import pytest
from unittest.mock import patch, MagicMock
import datetime


class TestSendEventReminders:
    """Tests for event reminder task."""

    @pytest.fixture
    def event_reminder_setup(self, app):
        """Create test data for event reminder tests."""
        from models import db, User, Event, Item
        
        with app.app_context():
            # Create users
            owner = User(name="Gift Owner", email="owner@example.com")
            claimer = User(name="Gift Claimer", email="claimer@example.com")
            
            db.session.add_all([owner, claimer])
            db.session.commit()
            
            # Create event 7 days from now
            event = Event(
                name="Birthday Party",
                date=datetime.date.today() + datetime.timedelta(days=7),
                reminder_sent=False,
                created_by_id=owner.id
            )
            db.session.add(event)
            db.session.commit()
            
            # Create claimed item
            item = Item(
                description="Birthday Gift",
                user_id=owner.id,
                event_id=event.id,
                status="Claimed",
                last_updated_by_id=claimer.id
            )
            db.session.add(item)
            db.session.commit()
            
            return event.id, owner.id, claimer.id

    @patch('services.email_service.send_event_reminder')
    def test_send_event_reminders_sends_email(self, mock_send, app, event_reminder_setup):
        """Should send reminder email for upcoming event."""
        from services.tasks import send_event_reminders
        from models import db, Event, Item, User
        
        mock_send.return_value = True
        event_id, owner_id, claimer_id = event_reminder_setup
        
        stats = send_event_reminders(app, db, Event, Item, User)
        
        assert stats['events_processed'] == 1
        assert stats['emails_sent'] == 1
        assert stats['errors'] == 0
        mock_send.assert_called_once()
        
        # Verify event is marked as reminder sent
        with app.app_context():
            event = db.session.get(Event, event_id)
            assert event.reminder_sent is True

    @patch('services.email_service.send_event_reminder')
    def test_no_events_due(self, mock_send, app):
        """Should handle case when no events need reminders."""
        from services.tasks import send_event_reminders
        from models import db, Event, Item, User
        
        stats = send_event_reminders(app, db, Event, Item, User)
        
        assert stats['events_processed'] == 0
        assert stats['emails_sent'] == 0
        mock_send.assert_not_called()

    @patch('services.email_service.send_event_reminder')
    def test_event_no_claimed_items(self, mock_send, app):
        """Should mark event as processed even with no claimed items."""
        from services.tasks import send_event_reminders
        from models import db, Event, Item, User
        
        with app.app_context():
            user = User(name="Test User", email="test@example.com")
            db.session.add(user)
            db.session.commit()
            
            # Event in 7 days with no claimed items
            event = Event(
                name="Empty Event",
                date=datetime.date.today() + datetime.timedelta(days=7),
                reminder_sent=False,
                created_by_id=user.id
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id
        
        stats = send_event_reminders(app, db, Event, Item, User)
        
        assert stats['events_processed'] == 1
        assert stats['emails_sent'] == 0
        mock_send.assert_not_called()
        
        with app.app_context():
            event = db.session.get(Event, event_id)
            assert event.reminder_sent is True

    @patch('services.email_service.send_event_reminder')
    def test_email_failure_handled(self, mock_send, app, event_reminder_setup):
        """Should handle email send failure gracefully."""
        from services.tasks import send_event_reminders
        from models import db, Event, Item, User
        
        mock_send.return_value = False
        
        stats = send_event_reminders(app, db, Event, Item, User)
        
        assert stats['events_processed'] == 1
        assert stats['errors'] == 1

    @patch('services.email_service.send_event_reminder')
    def test_email_exception_handled(self, mock_send, app, event_reminder_setup):
        """Should handle email exception gracefully."""
        from services.tasks import send_event_reminders
        from models import db, Event, Item, User
        
        mock_send.side_effect = Exception("SMTP Error")
        
        stats = send_event_reminders(app, db, Event, Item, User)
        
        assert stats['events_processed'] == 1
        assert stats['errors'] == 1
