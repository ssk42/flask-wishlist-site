"""Tests for the Events CRUD functionality."""
import datetime
import pytest
from models import db, User, Event, Item


@pytest.fixture
def event_owner(app):
    """Create a user who will own events."""
    with app.app_context():
        user = User(name="Event Owner", email="owner@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def other_event_user(app):
    """Create another user for permission tests."""
    with app.app_context():
        user = User(name="Other User", email="other@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def login_event_owner(client, event_owner):
    """Log in as the event owner."""
    with client.session_transaction() as session:
        session["_user_id"] = str(event_owner)
        session["_fresh"] = True
    return event_owner


@pytest.fixture
def login_other_user(client, other_event_user):
    """Log in as another user."""
    with client.session_transaction() as session:
        session["_user_id"] = str(other_event_user)
        session["_fresh"] = True
    return other_event_user


class TestEventsPage:
    """Tests for the /events route."""

    def test_events_requires_authentication(self, client):
        """Events page should require login."""
        response = client.get('/events')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_events_page_loads(self, client, login_event_owner):
        """Events page should load for authenticated user."""
        response = client.get('/events')
        assert response.status_code == 200
        assert b'Events' in response.data

    def test_events_shows_upcoming_and_past(self, app, client, login_event_owner):
        """Events should be grouped into upcoming and past."""
        with app.app_context():
            today = datetime.date.today()
            upcoming = Event(
                name="Future Event",
                date=today + datetime.timedelta(days=30),
                created_by_id=login_event_owner
            )
            past = Event(
                name="Past Event",
                date=today - datetime.timedelta(days=30),
                created_by_id=login_event_owner
            )
            db.session.add_all([upcoming, past])
            db.session.commit()

        response = client.get('/events')
        assert response.status_code == 200
        assert b'Future Event' in response.data
        assert b'Past Event' in response.data
        assert b'Upcoming Events' in response.data
        assert b'Past Events' in response.data


class TestCreateEvent:
    """Tests for creating events."""

    def test_new_event_page_loads(self, client, login_event_owner):
        """New event form should load."""
        response = client.get('/events/new')
        assert response.status_code == 200
        assert b'New Event' in response.data

    def test_create_event_success(self, app, client, login_event_owner):
        """Creating an event should work with valid data."""
        response = client.post('/events/new', data={
            'name': 'Christmas 2025',
            'date': '2025-12-25'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Christmas 2025' in response.data
        assert b'created successfully' in response.data

        with app.app_context():
            event = Event.query.filter_by(name='Christmas 2025').first()
            assert event is not None
            assert event.date == datetime.date(2025, 12, 25)
            assert event.created_by_id == login_event_owner

    def test_create_event_requires_name(self, client, login_event_owner):
        """Event name is required."""
        response = client.post('/events/new', data={
            'name': '',
            'date': '2025-12-25'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Event name is required' in response.data

    def test_create_event_requires_date(self, client, login_event_owner):
        """Event date is required."""
        response = client.post('/events/new', data={
            'name': 'Test Event',
            'date': ''
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Event date is required' in response.data

    def test_create_event_invalid_date(self, client, login_event_owner):
        """Invalid date format should show error."""
        response = client.post('/events/new', data={
            'name': 'Test Event',
            'date': 'not-a-date'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Invalid date format' in response.data


class TestEditEvent:
    """Tests for editing events."""

    def test_edit_event_page_loads(self, app, client, login_event_owner):
        """Edit event form should load for owner."""
        with app.app_context():
            event = Event(
                name="Test Event",
                date=datetime.date(2025, 6, 15),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = client.get(f'/events/{event_id}/edit')
        assert response.status_code == 200
        assert b'Edit Event' in response.data
        assert b'Test Event' in response.data

    def test_edit_event_success(self, app, client, login_event_owner):
        """Editing an event should work."""
        with app.app_context():
            event = Event(
                name="Original Name",
                date=datetime.date(2025, 6, 15),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = client.post(f'/events/{event_id}/edit', data={
            'name': 'Updated Name',
            'date': '2025-07-20'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Updated Name' in response.data
        assert b'updated successfully' in response.data

    def test_edit_event_only_owner_can_edit(self, app, client, login_event_owner, login_other_user):
        """Only the event creator can edit."""
        with app.app_context():
            event = Event(
                name="Owner's Event",
                date=datetime.date(2025, 6, 15),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        # Log in as other user
        with client.session_transaction() as session:
            session["_user_id"] = str(login_other_user)
            session["_fresh"] = True

        response = client.get(f'/events/{event_id}/edit', follow_redirects=True)
        assert response.status_code == 200
        assert b'only edit events you created' in response.data

    def test_edit_event_not_found(self, client, login_event_owner):
        """Editing non-existent event returns 404."""
        response = client.get('/events/99999/edit')
        assert response.status_code == 404

    def test_edit_event_missing_name_shows_error(self, app, client, login_event_owner):
        """Editing an event with empty name should show validation error."""
        with app.app_context():
            event = Event(
                name="Original Name",
                date=datetime.date(2025, 6, 15),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = client.post(f'/events/{event_id}/edit', data={
            'name': '',
            'date': '2025-07-20'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Event name is required' in response.data

    def test_edit_event_missing_date_shows_error(self, app, client, login_event_owner):
        """Editing an event with empty date should show validation error."""
        with app.app_context():
            event = Event(
                name="Original Name",
                date=datetime.date(2025, 6, 15),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = client.post(f'/events/{event_id}/edit', data={
            'name': 'Updated Name',
            'date': ''
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Event date is required' in response.data

    def test_edit_event_invalid_date_shows_error(self, app, client, login_event_owner):
        """Editing an event with invalid date format should show validation error."""
        with app.app_context():
            event = Event(
                name="Original Name",
                date=datetime.date(2025, 6, 15),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = client.post(f'/events/{event_id}/edit', data={
            'name': 'Updated Name',
            'date': 'not-a-valid-date'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Invalid date format' in response.data


class TestDeleteEvent:
    """Tests for deleting events."""

    def test_delete_event_success(self, app, client, login_event_owner):
        """Deleting an event should work."""
        with app.app_context():
            event = Event(
                name="To Delete",
                date=datetime.date(2025, 6, 15),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = client.post(f'/events/{event_id}/delete', follow_redirects=True)
        assert response.status_code == 200
        assert b'deleted' in response.data

        with app.app_context():
            assert Event.query.get(event_id) is None

    def test_delete_event_only_owner_can_delete(self, app, client, login_event_owner, login_other_user):
        """Only the event creator can delete."""
        with app.app_context():
            event = Event(
                name="Owner's Event",
                date=datetime.date(2025, 6, 15),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        # Log in as other user
        with client.session_transaction() as session:
            session["_user_id"] = str(login_other_user)
            session["_fresh"] = True

        response = client.post(f'/events/{event_id}/delete', follow_redirects=True)
        assert response.status_code == 200
        assert b'only delete events you created' in response.data

        # Event should still exist
        with app.app_context():
            assert Event.query.get(event_id) is not None

    def test_delete_event_clears_item_associations(self, app, client, login_event_owner):
        """Deleting an event should unlink items but not delete them."""
        with app.app_context():
            event = Event(
                name="Event with Items",
                date=datetime.date(2025, 6, 15),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

            item = Item(
                description="Associated Item",
                user_id=login_event_owner,
                event_id=event_id
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        response = client.post(f'/events/{event_id}/delete', follow_redirects=True)
        assert response.status_code == 200

        # Item should still exist but no longer associated
        with app.app_context():
            item = Item.query.get(item_id)
            assert item is not None
            assert item.event_id is None

    def test_delete_event_nonexistent_returns_404(self, client, login_event_owner):
        """Deleting a non-existent event returns 404."""
        response = client.post('/events/99999/delete')
        assert response.status_code == 404


class TestEventItemAssociation:
    """Tests for associating items with events."""

    def test_submit_item_with_event(self, app, client, login_event_owner):
        """Items can be associated with events during creation."""
        with app.app_context():
            event = Event(
                name="Birthday",
                date=datetime.date.today() + datetime.timedelta(days=30),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        response = client.post('/submit_item', data={
            'description': 'Birthday Gift',
            'event_id': event_id,
            'priority': 'High'
        }, follow_redirects=True)

        assert response.status_code == 200

        with app.app_context():
            item = Item.query.filter_by(description='Birthday Gift').first()
            assert item is not None
            assert item.event_id == event_id

    def test_edit_item_event_association(self, app, client, login_event_owner):
        """Items can have their event association updated."""
        with app.app_context():
            event = Event(
                name="Holiday",
                date=datetime.date.today() + datetime.timedelta(days=30),
                created_by_id=login_event_owner
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

            item = Item(
                description="Test Item",
                user_id=login_event_owner,
                priority="High"
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        response = client.post(f'/edit_item/{item_id}', data={
            'description': 'Test Item',
            'event_id': event_id,
            'priority': 'High'
        }, follow_redirects=True)

        assert response.status_code == 200

        with app.app_context():
            item = Item.query.get(item_id)
            assert item.event_id == event_id
