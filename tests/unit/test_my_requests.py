"""Tests for the My Requests view (#88): the signed-in user's own requested gifts."""
import datetime

from models import db, Item


def _make_item(app, description, owner_id, archived=False, status="Available"):
    with app.app_context():
        item = Item(description=description, user_id=owner_id, status=status)
        if archived:
            item.archived_at = datetime.datetime.now(datetime.timezone.utc)
        db.session.add(item)
        db.session.commit()
        return item.id


class TestMyRequests:
    def test_requires_login(self, app, client):
        response = client.get("/my-requests")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_shows_only_own_active_items(self, app, client, login, user, other_user):
        # @spec OWN-ITEM-018
        _make_item(app, "Mine active", user)
        _make_item(app, "Mine archived", user, archived=True)
        _make_item(app, "Theirs active", other_user)

        response = client.get("/my-requests")

        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "Mine active" in body
        assert "Mine archived" not in body
        assert "Theirs active" not in body

    def test_newest_first(self, app, client, login, user):
        # @spec OWN-ITEM-018
        _make_item(app, "Older request", user)
        _make_item(app, "Newer request", user)

        body = client.get("/my-requests").get_data(as_text=True)

        assert body.index("Newer request") < body.index("Older request")

    def test_empty_state(self, app, client, login, user):
        response = client.get("/my-requests")
        assert response.status_code == 200
        assert "haven't requested" in response.get_data(as_text=True)
