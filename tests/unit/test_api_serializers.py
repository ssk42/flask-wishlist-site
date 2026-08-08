"""Tests for API serializers — surprise protection is the contract here."""

from models import db, User, Item, Notification
from services.api_serializers import serialize_item, serialize_notification, serialize_user


def _make_claimed_item(owner_id, claimer_id):
    item = Item(
        description="Mystery Gift",
        user_id=owner_id,
        status="Claimed",
        last_updated_by_id=claimer_id,
        price=19.99,
    )
    db.session.add(item)
    db.session.commit()
    return item


def test_owner_never_sees_status_or_claimer(app, user, other_user):
    with app.app_context():
        item = _make_claimed_item(owner_id=user, claimer_id=other_user)
        owner = db.session.get(User, user)

        data = serialize_item(item, viewer=owner)

        assert "status" not in data
        assert "last_updated_by" not in data
        assert data["description"] == "Mystery Gift"
        assert data["price"] == 19.99


def test_non_owner_sees_status_and_claimer(app, user, other_user):
    with app.app_context():
        item = _make_claimed_item(owner_id=user, claimer_id=other_user)
        viewer = db.session.get(User, other_user)

        data = serialize_item(item, viewer=viewer)

        assert data["status"] == "Claimed"
        assert data["last_updated_by"] == {"id": other_user, "name": "Other User"}


def test_serialize_user_with_optional_item_count(app, user):
    with app.app_context():
        u = db.session.get(User, user)
        assert "item_count" not in serialize_user(u)
        assert serialize_user(u, item_count=3)["item_count"] == 3


def test_serialize_notification(app, user):
    with app.app_context():
        notif = Notification(user_id=user, message="hi", link="/items")
        db.session.add(notif)
        db.session.commit()

        data = serialize_notification(notif)

        assert data["message"] == "hi"
        assert data["is_read"] is False
        assert data["created_at"] is not None
