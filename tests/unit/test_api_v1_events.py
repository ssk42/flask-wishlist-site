"""Tests for API v1 events read endpoints: list + detail (strict tests-first)."""

import datetime

from models import db, Event, Item


def _auth(client, email="test@example.com"):
    response = client.post("/api/v1/auth/login",
                           json={"email": email, "family_code": "testsecret"})
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def _seed(app, user, other_user):
    with app.app_context():
        birthday = Event(name="Birthday", date=datetime.date(2026, 12, 25),
                         created_by_id=user, reminder_sent=True)
        reunion = Event(name="Reunion", date=datetime.date(2025, 1, 5),
                        created_by_id=other_user)
        db.session.add_all([birthday, reunion])
        db.session.flush()
        db.session.add_all([
            Item(description="Own available", user_id=user, status="Available",
                 event_id=birthday.id),
            Item(description="Own claimed secretly", user_id=user, status="Claimed",
                 last_updated_by_id=other_user, event_id=birthday.id),
            Item(description="Old archived", user_id=user, status="Available",
                 event_id=birthday.id,
                 archived_at=datetime.datetime(2026, 1, 1)),
        ])
        db.session.commit()
        return birthday.id, reunion.id


# @spec OWN-EVT-010
def test_events_list_shape_and_date_format(app, client, user, other_user):
    birthday_id, reunion_id = _seed(app, user, other_user)
    response = client.get("/api/v1/events", headers=_auth(client))

    assert response.status_code == 200
    events = response.get_json()["events"]
    assert isinstance(events, list) and len(events) == 2
    by_name = {e["name"]: e for e in events}
    assert set(by_name["Birthday"]) >= {"id", "name", "date", "created_by", "item_count"}
    assert by_name["Birthday"]["date"] == "2026-12-25"
    assert by_name["Reunion"]["date"] == "2025-01-05"
    assert by_name["Birthday"]["id"] == birthday_id
    assert by_name["Birthday"]["created_by"] == {"id": user, "name": "Test User"}
    assert by_name["Reunion"]["created_by"] == {"id": other_user, "name": "Other User"}
    assert "reminder_sent" not in by_name["Birthday"]


# @spec OWN-EVT-010
def test_events_list_item_count_excludes_archived(app, client, user, other_user):
    _seed(app, user, other_user)
    events = {e["name"]: e
              for e in client.get("/api/v1/events", headers=_auth(client)).get_json()["events"]}
    assert events["Birthday"]["item_count"] == 2
    assert events["Reunion"]["item_count"] == 0


# @spec OWN-EVT-010
def test_events_list_empty(app, client, user):
    response = client.get("/api/v1/events", headers=_auth(client))

    assert response.status_code == 200
    assert response.get_json()["events"] == []


# @spec OWN-EVT-010
def test_events_list_requires_auth(app, client, user, other_user):
    _seed(app, user, other_user)
    assert client.get("/api/v1/events").status_code == 401


# @spec OWN-EVT-011
def test_event_detail_items_masked_for_owner(app, client, user, other_user):
    birthday_id, _ = _seed(app, user, other_user)
    response = client.get(f"/api/v1/events/{birthday_id}", headers=_auth(client))

    assert response.status_code == 200
    body = response.get_json()
    assert body["event"]["name"] == "Birthday"
    assert body["event"]["date"] == "2026-12-25"
    assert body["event"]["item_count"] == 2
    assert "reminder_sent" not in body["event"]
    items = {i["description"]: i for i in body["items"]}
    assert set(items) == {"Own available", "Own claimed secretly"}
    # Surprise protection: owner's own items carry no claim data.
    assert "status" not in items["Own available"]
    assert "last_updated_by" not in items["Own claimed secretly"]


# @spec OWN-EVT-011
def test_event_detail_shows_status_on_others_items(app, client, user, other_user):
    birthday_id, _ = _seed(app, user, other_user)
    with app.app_context():
        db.session.add(Item(description="Their gift", user_id=other_user,
                            status="Claimed", last_updated_by_id=user,
                            event_id=birthday_id))
        db.session.commit()
    items = {i["description"]: i for i in
             client.get(f"/api/v1/events/{birthday_id}",
                        headers=_auth(client)).get_json()["items"]}
    assert items["Their gift"]["status"] == "Claimed"
    assert items["Their gift"]["last_updated_by"] == {"id": user, "name": "Test User"}


# @spec OWN-EVT-011
def test_event_detail_zero_items(app, client, user, other_user):
    _, reunion_id = _seed(app, user, other_user)
    response = client.get(f"/api/v1/events/{reunion_id}", headers=_auth(client))

    assert response.status_code == 200
    assert response.get_json()["items"] == []
    assert response.get_json()["event"]["item_count"] == 0


# @spec OWN-EVT-011
def test_event_detail_not_found(app, client, user):
    response = client.get("/api/v1/events/999999", headers=_auth(client))

    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}


# @spec OWN-EVT-011
def test_event_detail_requires_auth(app, client, user, other_user):
    birthday_id, _ = _seed(app, user, other_user)
    assert client.get(f"/api/v1/events/{birthday_id}").status_code == 401


# @spec OWN-EVT-012
def test_events_create_ok(app, client, user):
    response = client.post("/api/v1/events", headers=_auth(client),
                           json={"name": "Shower", "date": "2027-05-01"})
    assert response.status_code == 201
    event = response.get_json()["event"]
    assert event["name"] == "Shower"
    assert event["date"] == "2027-05-01"
    assert event["created_by"] == {"id": user, "name": "Test User"}
    assert event["item_count"] == 0
    assert "reminder_sent" not in event


# @spec OWN-EVT-012
def test_events_create_400_missing_date(app, client, user):
    response = client.post("/api/v1/events", headers=_auth(client),
                           json={"name": "No date"})
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert len(errors) > 0


# @spec OWN-EVT-012
def test_events_create_400_bad_date(app, client, user):
    response = client.post("/api/v1/events", headers=_auth(client),
                           json={"name": "Shower", "date": "05/01/2027"})
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert len(errors) > 0


# @spec OWN-EVT-012
def test_events_create_400_blank_name(app, client, user):
    response = client.post("/api/v1/events", headers=_auth(client),
                           json={"name": "   ", "date": "2027-05-01"})
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert len(errors) > 0


# @spec OWN-EVT-012
def test_events_create_401_without_token(app, client, user):
    response = client.post("/api/v1/events",
                           json={"name": "Shower", "date": "2027-05-01"})
    assert response.status_code == 401


# @spec OWN-EVT-013
def test_events_edit_ok_partial_name(app, client, user):
    created = client.post("/api/v1/events", headers=_auth(client),
                          json={"name": "Original", "date": "2027-06-01"})
    event_id = created.get_json()["event"]["id"]
    response = client.patch(f"/api/v1/events/{event_id}", headers=_auth(client),
                            json={"name": "Renamed"})
    assert response.status_code == 200
    event = response.get_json()["event"]
    assert event["name"] == "Renamed"
    assert event["date"] == "2027-06-01"


# @spec OWN-EVT-013
def test_events_edit_ok_date(app, client, user):
    created = client.post("/api/v1/events", headers=_auth(client),
                          json={"name": "Original", "date": "2027-06-01"})
    event_id = created.get_json()["event"]["id"]
    response = client.patch(f"/api/v1/events/{event_id}", headers=_auth(client),
                            json={"date": "2027-07-04"})
    assert response.status_code == 200
    event = response.get_json()["event"]
    assert event["name"] == "Original"
    assert event["date"] == "2027-07-04"


# @spec OWN-EVT-013
def test_events_edit_403_non_creator(app, client, user, other_user):
    created = client.post("/api/v1/events",
                          headers=_auth(client, email="other@example.com"),
                          json={"name": "Theirs", "date": "2027-06-01"})
    event_id = created.get_json()["event"]["id"]
    response = client.patch(f"/api/v1/events/{event_id}", headers=_auth(client),
                            json={"name": "Hacked"})
    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}


# @spec OWN-EVT-013
def test_events_edit_404(app, client, user):
    response = client.patch("/api/v1/events/999999", headers=_auth(client),
                            json={"name": "Ghost"})
    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}


# @spec OWN-EVT-013
def test_events_edit_400_bad_date(app, client, user):
    created = client.post("/api/v1/events", headers=_auth(client),
                          json={"name": "Original", "date": "2027-06-01"})
    event_id = created.get_json()["event"]["id"]
    response = client.patch(f"/api/v1/events/{event_id}", headers=_auth(client),
                            json={"date": "not-a-date"})
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert len(errors) > 0


# @spec OWN-EVT-014
def test_events_delete_ok_unlinks_items(app, client, user):
    created = client.post("/api/v1/events", headers=_auth(client),
                          json={"name": "Doomed", "date": "2027-08-01"})
    event_id = created.get_json()["event"]["id"]
    with app.app_context():
        db.session.add(Item(description="Kept gift", user_id=user,
                            status="Available", event_id=event_id))
        db.session.commit()
    response = client.delete(f"/api/v1/events/{event_id}", headers=_auth(client))
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    with app.app_context():
        assert db.session.get(Event, event_id) is None
        kept = Item.query.filter_by(description="Kept gift").one()
        assert kept.event_id is None


# @spec OWN-EVT-014
def test_events_delete_403_non_creator(app, client, user, other_user):
    created = client.post("/api/v1/events",
                          headers=_auth(client, email="other@example.com"),
                          json={"name": "Theirs", "date": "2027-06-01"})
    event_id = created.get_json()["event"]["id"]
    response = client.delete(f"/api/v1/events/{event_id}", headers=_auth(client))
    assert response.status_code == 403
    assert response.get_json() == {"error": "forbidden"}


# @spec OWN-EVT-014
def test_events_delete_404(app, client, user):
    response = client.delete("/api/v1/events/999999", headers=_auth(client))
    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}
