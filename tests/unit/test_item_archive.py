"""Tests for Wishlist Archive (#46): owner-only soft-delete via Item.archived_at."""
import datetime
from models import db, Event, Item, User


def _login_as(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def _make_item(app, description, owner_id, status="Available", claimer_id=None):
    with app.app_context():
        item = Item(description=description, user_id=owner_id, status=status,
                    last_updated_by_id=claimer_id)
        db.session.add(item)
        db.session.commit()
        return item.id


def _archive(app, item_id):
    with app.app_context():
        item = db.session.get(Item, item_id)
        item.archived_at = datetime.datetime.now(datetime.timezone.utc)
        db.session.commit()


def _v1_headers(client, email="test@example.com"):
    response = client.post("/api/v1/auth/login",
                           json={"email": email, "family_code": "testsecret"})
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


class TestArchiveTransitions:
    def test_owner_can_archive(self, app, client, login, user):
        # @spec OWN-ITEM-009
        item_id = _make_item(app, "Archive me", user)
        response = client.post(f"/archive_item/{item_id}")

        assert response.status_code == 302
        with app.app_context():
            assert db.session.get(Item, item_id).archived_at is not None

    def test_non_owner_archive_denied(self, app, client, user, other_user):
        # @spec OWN-ITEM-010
        _login_as(client, other_user)
        item_id = _make_item(app, "Not yours", user)
        response = client.post(f"/archive_item/{item_id}")

        assert response.status_code == 302
        with app.app_context():
            assert db.session.get(Item, item_id).archived_at is None

    def test_unarchive_restores_status_and_claim(self, app, client, login, user,
                                                 other_user):
        # @spec OWN-ITEM-011
        item_id = _make_item(app, "Claimed gadget", user, status="Claimed",
                             claimer_id=other_user)
        client.post(f"/archive_item/{item_id}")
        client.post(f"/unarchive_item/{item_id}")

        with app.app_context():
            item = db.session.get(Item, item_id)
            assert item.archived_at is None
            assert item.status == "Claimed"
            assert item.last_updated_by_id == other_user

    def test_rearchive_and_unarchive_active_are_noops(self, app, client, login,
                                                      user):
        # @spec OWN-ITEM-017
        item_id = _make_item(app, "Twice", user)
        client.post(f"/archive_item/{item_id}")
        with app.app_context():
            first = db.session.get(Item, item_id).archived_at
        client.post(f"/archive_item/{item_id}")
        with app.app_context():
            assert db.session.get(Item, item_id).archived_at == first

        active_id = _make_item(app, "Active", user)
        client.post(f"/unarchive_item/{active_id}")
        with app.app_context():
            assert db.session.get(Item, active_id).archived_at is None


class TestArchivedHiddenEverywhere:
    def test_archived_hidden_from_list_dashboard_and_claims(
            self, app, client, user, other_user):
        # @spec OWN-ITEM-012
        _login_as(client, other_user)
        item_id = _make_item(app, "Hidden gadget", user, status="Claimed",
                             claimer_id=other_user)
        _archive(app, item_id)

        assert b"Hidden gadget" not in client.get("/items").data
        assert b"Hidden gadget" not in client.get("/").data
        assert b"Hidden gadget" not in client.get("/my-claims").data

    def test_archived_hidden_from_api_v1(self, app, client, user, other_user):
        # @spec OWN-ITEM-012
        item_id = _make_item(app, "Hidden gadget", other_user)
        headers = _v1_headers(client)
        _archive(app, item_id)

        items = client.get("/api/v1/items", headers=headers).get_json()["items"]
        assert [i["description"] for i in items] == []
        assert client.get(f"/api/v1/items/{item_id}",
                          headers=headers).status_code == 404

    def test_archived_view_shows_only_owners_archived(
            self, app, client, user, other_user):
        # @spec OWN-ITEM-016
        _login_as(client, user)
        mine = _make_item(app, "Mine archived", user)
        _make_item(app, "Mine active", user)
        theirs = _make_item(app, "Theirs archived", other_user)
        _archive(app, mine)
        _archive(app, theirs)

        data = client.get("/items?status=Archived").data
        assert b"Mine archived" in data
        assert b"Mine active" not in data
        assert b"Theirs archived" not in data


class TestArchivedRejectsActions:
    def test_claim_comment_and_refresh_rejected(
            self, app, client, user, other_user):
        # @spec OWN-ITEM-013
        _login_as(client, other_user)
        item_id = _make_item(app, "Hands off", user)
        _archive(app, item_id)

        assert client.post(f"/claim_item/{item_id}").status_code == 302
        assert client.post(f"/item/{item_id}/comment",
                           data={"content": "hello"}).status_code == 302
        assert client.post(
            f"/item/{item_id}/refresh-price").status_code == 302
        with app.app_context():
            item = db.session.get(Item, item_id)
            assert item.status == "Available"
            assert len(item.comments) == 0

    def test_edit_archived_stays_archived(self, app, client, login, user):
        # @spec OWN-ITEM-014
        item_id = _make_item(app, "Edit me", user)
        client.post(f"/archive_item/{item_id}")
        client.post(f"/edit_item/{item_id}",
                    data={"description": "Edited", "status": "Available",
                          "priority": "Low"})

        with app.app_context():
            item = db.session.get(Item, item_id)
            assert item.description == "Edited"
            assert item.archived_at is not None

    def test_v1_claim_and_update_on_archived_404(
            self, app, client, user, other_user):
        # @spec OWN-ITEM-013
        item_id = _make_item(app, "V1 hands off", user)
        owner_headers = _v1_headers(client)
        giver_headers = _v1_headers(client, email="other@example.com")
        _archive(app, item_id)

        assert client.post(f"/api/v1/items/{item_id}/claim",
                           headers=giver_headers).status_code == 404
        assert client.patch(f"/api/v1/items/{item_id}",
                            json={"description": "X"},
                            headers=owner_headers).status_code == 404


class TestArchivedExcludedFromCrawler:
    def test_stale_selection_skips_archived(self, app, user):
        # @spec OWN-ITEM-015
        import datetime as dt

        from services.price_service import get_items_needing_update

        with app.app_context():
            stale = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
            live = Item(description="Live", user_id=user, status="Available",
                        link="https://example.com/a", price_updated_at=stale)
            buried = Item(description="Buried", user_id=user,
                          status="Available", link="https://example.com/b",
                          price_updated_at=stale)
            db.session.add_all([live, buried])
            db.session.commit()
            buried.archived_at = dt.datetime.now(dt.timezone.utc)
            db.session.commit()

            cutoff = (dt.datetime.now(dt.timezone.utc)
                      - dt.timedelta(days=7))
            descriptions = [i.description for i in get_items_needing_update(
                Item, db, cutoff)]
            assert "Live" in descriptions
            assert "Buried" not in descriptions


class TestArchivedSecondarySurfaces:
    def test_export_excludes_archived(self, app, client, user, other_user):
        # @spec OWN-ITEM-012
        import io

        import pandas as pd

        _login_as(client, other_user)
        live_id = _make_item(app, "Live claim", user, status="Claimed",
                             claimer_id=other_user)
        buried_id = _make_item(app, "Buried claim", user, status="Claimed",
                               claimer_id=other_user)
        _archive(app, buried_id)

        try:
            response = client.get("/export_my_status_updates")
            assert response.status_code == 200
            descriptions = pd.read_excel(io.BytesIO(response.data))["Description"].tolist()
            assert descriptions == ["Live claim"]
        finally:
            import os
            litter = "status_updates_by_Other User.xlsx"
            if os.path.exists(litter):
                os.remove(litter)

    def test_users_count_excludes_archived(self, app, client, user):
        # @spec OWN-ITEM-012
        _make_item(app, "Live", user)
        hidden_id = _make_item(app, "Hidden", user)
        _archive(app, hidden_id)

        users = {u["name"]: u for u in client.get(
            "/api/v1/users", headers=_v1_headers(client)).get_json()["users"]}
        assert users["Test User"]["item_count"] == 1

    def test_reminders_skip_archived(self, app, user, other_user):
        # @spec OWN-ITEM-012
        import datetime as dt
        from unittest.mock import patch

        from models import Event
        from services.tasks import send_event_reminders

        with app.app_context():
            event = Event(name="Party",
                          date=dt.date.today() + dt.timedelta(days=7),
                          created_by_id=user, reminder_sent=False)
            db.session.add(event)
            db.session.commit()
            live = Item(description="Live gift", user_id=user,
                        status="Claimed", event_id=event.id,
                        last_updated_by_id=other_user)
            buried = Item(description="Buried gift", user_id=user,
                          status="Claimed", event_id=event.id,
                          last_updated_by_id=other_user)
            db.session.add_all([live, buried])
            db.session.commit()
            buried.archived_at = dt.datetime.now(dt.timezone.utc)
            db.session.commit()
            event_id = event.id

        with patch("services.email_service.send_event_reminder",
                   return_value=True) as mock_send:
            stats = send_event_reminders(app, db, Event, Item, User)

        assert stats["emails_sent"] == 1
        sent = mock_send.call_args.kwargs["claimed_items"]
        assert [i["description"] for i in sent] == ["Live gift"]


    def test_full_export_excludes_archived(self, app, client, login, user):
        # @spec OWN-ITEM-012
        import io

        import pandas as pd

        _make_item(app, "Live export", user)
        hidden_id = _make_item(app, "Hidden export", user)
        _archive(app, hidden_id)

        try:
            response = client.get("/export_items")
            assert response.status_code == 200
            descriptions = pd.read_excel(io.BytesIO(response.data))["Description"].tolist()
            assert descriptions == ["Live export"]
        finally:
            import os
            if os.path.exists("allWishlistItems.xlsx"):
                os.remove("allWishlistItems.xlsx")

    def test_contributions_exclude_archived(self, app, client, user, other_user):
        # @spec OWN-ITEM-012
        from models import Contribution

        _login_as(client, other_user)
        with app.app_context():
            live = Item(description="Live split", user_id=user,
                        status="Splitting", price=100.0)
            buried = Item(description="Buried split", user_id=user,
                          status="Splitting", price=100.0)
            db.session.add_all([live, buried])
            db.session.commit()
            db.session.add_all([
                Contribution(item_id=live.id, user_id=other_user, amount=10.0),
                Contribution(item_id=buried.id, user_id=other_user, amount=10.0),
            ])
            db.session.commit()
            buried.archived_at = datetime.datetime.now(datetime.timezone.utc)
            db.session.commit()

        data = client.get("/my-claims").data
        assert b"Live split" in data
        assert b"Buried split" not in data

    def test_event_badge_excludes_archived(self, app, client, login, user):
        # @spec OWN-ITEM-012
        import datetime as dt

        with app.app_context():
            event = Event(name="Gala",
                          date=dt.date.today() + dt.timedelta(days=7),
                          created_by_id=user, reminder_sent=False)
            db.session.add(event)
            db.session.commit()
            live = Item(description="Live favor", user_id=user,
                        event_id=event.id)
            buried = Item(description="Buried favor", user_id=user,
                          event_id=event.id)
            db.session.add_all([live, buried])
            db.session.commit()
            buried.archived_at = dt.datetime.now(dt.timezone.utc)
            db.session.commit()

        assert b"1 items" in client.get("/events").data