"""
Tests for filter persistence functionality.
Ensures that filters are saved to session and persist across user actions.
"""

import pytest
from app import db, User, Item, Event, STATUS_CHOICES, PRIORITY_CHOICES


def login_via_post(client, email):
    """Helper to login via POST request."""
    return client.post("/login", data={"email": email}, follow_redirects=True)


class TestFilterPersistence:
    """Test filter persistence across user sessions and actions."""

    # ... (skipping unchanged part) ...

    def test_filter_persistence_with_whitespace_handling(self, client, app, login, user):
        """Test that whitespace in filters is handled correctly."""
        with app.app_context():
            event = Event(name="Test Event", date=datetime.date(2025, 12, 25))
            db.session.add(event)
            db.session.commit()
            event_id = event.id
            
            db.session.add(
                Item(
                    description="Test Item",
                    status="Available",
                    priority="High",
                    category="Electronics",
                    event_id=event_id,
                    user_id=user,
                )
            )
            db.session.commit()

        # Apply filters with whitespace
        response = client.get("/items", query_string={
            "event_filter": f"  {event_id}  ",
