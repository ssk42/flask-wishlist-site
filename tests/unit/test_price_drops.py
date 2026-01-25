"""Tests for Price Drop Alerts feature."""
import pytest
from unittest.mock import patch
import datetime


def login_via_post(client, email):
    return client.post(
        "/login",
        data={
            "email": email,
            "password": "testsecret"},
        follow_redirects=True)


@pytest.fixture
def price_drop_setup(app):
    """Create test data for price drop tests."""
    from models import db, User, Item

    with app.app_context():
        # Owner
        owner = User(name="Alice", email="alice@example.com")
        # Claimer
        claimer = User(name="Bob", email="bob@example.com")

        db.session.add_all([owner, claimer])
        db.session.commit()

        # Item with old price, claimed by Bob
        item = Item(
            description="Nintendo Switch",
            link="https://example.com/switch",
            price=299.99,
            user_id=owner.id,
            status="Claimed",
            last_updated_by_id=claimer.id,
            price_updated_at=datetime.datetime.now(
                datetime.timezone.utc) -
            datetime.timedelta(
                days=8))
        db.session.add(item)
        db.session.commit()

        return owner.id, claimer.id, item.id, item.link


def test_price_drop_creates_owner_notification(app, price_drop_setup):
    """When price drops ≥10%, owner gets a notification."""
    from services.price_service import update_stale_prices
    from models import db, Item, Notification

    owner_id, claimer_id, item_id, item_link = price_drop_setup

    # Mock asyncio.run to return our fake results
    with patch('asyncio.run') as mock_asyncio_run:
        # Simulate 15% price drop: $299.99 -> $254.99
        mock_asyncio_run.return_value = {item_link: 254.99}

        with app.app_context():
            stats = update_stale_prices(app, db, Item, Notification)

            assert stats['price_drops'] == 1

            # Owner should have notification
            owner_notif = Notification.query.filter_by(
                user_id=owner_id).first()
            assert owner_notif is not None
            assert "price drop" in owner_notif.message.lower()
            assert "Nintendo Switch" in owner_notif.message


def test_price_drop_creates_claimer_notification(app, price_drop_setup):
    """When price drops ≥10%, claimer also gets a notification."""
    from services.price_service import update_stale_prices
    from models import db, Item, Notification

    owner_id, claimer_id, item_id, item_link = price_drop_setup

    with patch('asyncio.run') as mock_asyncio_run:
        mock_asyncio_run.return_value = {item_link: 254.99}  # 15% drop

        with app.app_context():
            update_stale_prices(app, db, Item, Notification)

            # Claimer should have notification
            claimer_notif = Notification.query.filter_by(
                user_id=claimer_id).first()
            assert claimer_notif is not None
            assert "you claimed" in claimer_notif.message.lower()


def test_small_price_drop_no_notification(app, price_drop_setup):
    """When price drops <10%, no notification is created."""
    from services.price_service import update_stale_prices
    from models import db, Item, Notification

    owner_id, claimer_id, item_id, item_link = price_drop_setup

    with patch('asyncio.run') as mock_asyncio_run:
        # Simulate 5% drop: $299.99 -> $284.99
        mock_asyncio_run.return_value = {item_link: 284.99}

        with app.app_context():
            stats = update_stale_prices(app, db, Item, Notification)

            assert stats['price_drops'] == 0
            assert Notification.query.count() == 0


def test_price_increase_no_notification(app, price_drop_setup):
    """When price increases, no notification is created."""
    from services.price_service import update_stale_prices
    from models import db, Item, Notification

    owner_id, claimer_id, item_id, item_link = price_drop_setup

    with patch('asyncio.run') as mock_asyncio_run:
        mock_asyncio_run.return_value = {item_link: 349.99}  # Price went up

        with app.app_context():
            stats = update_stale_prices(app, db, Item, Notification)

            assert stats['price_drops'] == 0
            assert Notification.query.count() == 0
