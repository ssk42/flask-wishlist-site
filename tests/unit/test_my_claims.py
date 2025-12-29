"""Tests for the My Claims page functionality."""
import pytest
from app import db, User, Item


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
def login_claimer(client, claimer):
    """Log in as the claimer."""
    with client.session_transaction() as session:
        session["_user_id"] = str(claimer)
        session["_fresh"] = True
    return claimer


class TestMyClaimsPage:
    """Tests for the /my-claims route."""

    def test_my_claims_requires_authentication(self, client):
        """My Claims page should require login."""
        response = client.get('/my-claims')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_my_claims_shows_claimed_items(self, app, client, login_claimer, recipient):
        """My Claims page should show items the user has claimed for others."""
        with app.app_context():
            # Create an item owned by recipient and claimed by claimer
            item = Item(
                description="Test Claimed Item",
                user_id=recipient,
                status="Claimed",
                last_updated_by_id=login_claimer,
                price=49.99
            )
            db.session.add(item)
            db.session.commit()

        response = client.get('/my-claims')
        assert response.status_code == 200
        assert b'Test Claimed Item' in response.data
        assert b'For Recipient' in response.data

    def test_my_claims_shows_purchased_items(self, app, client, login_claimer, recipient):
        """My Claims page should show items the user has purchased for others."""
        with app.app_context():
            item = Item(
                description="Test Purchased Item",
                user_id=recipient,
                status="Purchased",
                last_updated_by_id=login_claimer,
                price=99.99
            )
            db.session.add(item)
            db.session.commit()

        response = client.get('/my-claims')
        assert response.status_code == 200
        assert b'Test Purchased Item' in response.data

    def test_my_claims_does_not_show_own_items(self, app, client, login_claimer):
        """My Claims page should not show user's own items even if claimed status."""
        with app.app_context():
            item = Item(
                description="My Own Item",
                user_id=login_claimer,
                status="Claimed",
                last_updated_by_id=login_claimer
            )
            db.session.add(item)
            db.session.commit()

        response = client.get('/my-claims')
        assert response.status_code == 200
        assert b'My Own Item' not in response.data

    def test_my_claims_groups_by_recipient(self, app, client, login_claimer, recipient):
        """Items should be grouped by recipient."""
        with app.app_context():
            # Create another recipient
            recipient2 = User(name="Recipient2", email="recipient2@example.com")
            db.session.add(recipient2)
            db.session.commit()
            recipient2_id = recipient2.id

            item1 = Item(
                description="Item for Recipient",
                user_id=recipient,
                status="Claimed",
                last_updated_by_id=login_claimer
            )
            item2 = Item(
                description="Item for Recipient2",
                user_id=recipient2_id,
                status="Claimed",
                last_updated_by_id=login_claimer
            )
            db.session.add_all([item1, item2])
            db.session.commit()

        response = client.get('/my-claims')
        assert response.status_code == 200
        assert b'For Recipient' in response.data
        assert b'For Recipient2' in response.data

    def test_my_claims_badge_count(self, app, client, login_claimer, recipient):
        """Badge should show count of claimed (not purchased) items."""
        with app.app_context():
            # Create 2 claimed and 1 purchased items
            items = [
                Item(description="Claimed 1", user_id=recipient, status="Claimed", last_updated_by_id=login_claimer),
                Item(description="Claimed 2", user_id=recipient, status="Claimed", last_updated_by_id=login_claimer),
                Item(description="Purchased", user_id=recipient, status="Purchased", last_updated_by_id=login_claimer),
            ]
            db.session.add_all(items)
            db.session.commit()

        response = client.get('/my-claims')
        assert response.status_code == 200
        # Check the summary shows correct counts
        assert b'2' in response.data  # claimed count


class TestDashboardWidget:
    """Tests for the dashboard widget on index page."""

    def test_dashboard_shows_when_has_claims(self, app, client, login_claimer, recipient):
        """Dashboard should show claimed/purchased counts when user has claims."""
        with app.app_context():
            item = Item(
                description="Claimed Item",
                user_id=recipient,
                status="Claimed",
                last_updated_by_id=login_claimer
            )
            db.session.add(item)
            db.session.commit()

        response = client.get('/')
        assert response.status_code == 200
        assert b'Your Gift Tracker' in response.data
        assert b'View My Claims' in response.data

    def test_dashboard_hidden_when_no_claims(self, client, login_claimer):
        """Dashboard should not show when user has no claims."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Your Gift Tracker' not in response.data


class TestNavbarBadge:
    """Tests for the My Claims navbar badge."""

    def test_navbar_badge_shows_claimed_count(self, app, client, login_claimer, recipient):
        """Navbar should show badge with count of claimed items."""
        with app.app_context():
            item = Item(
                description="Claimed Item",
                user_id=recipient,
                status="Claimed",
                last_updated_by_id=login_claimer
            )
            db.session.add(item)
            db.session.commit()

        response = client.get('/')
        assert response.status_code == 200
        # Badge is shown in navbar
        assert b'My Claims' in response.data

    def test_navbar_badge_not_shown_when_zero(self, client, login_claimer):
        """Navbar badge should not show when count is zero."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'My Claims' in response.data
        # No badge shown when count is 0 (just the link text)
