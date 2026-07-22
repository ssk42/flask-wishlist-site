"""Tests for API v1 write endpoints: item CRUD and claim actions."""

from models import db, Item


def _auth(client, email="test@example.com"):
    response = client.post("/api/v1/auth/login",
                           json={"email": email, "family_code": "testsecret"})
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def _make_item(app, owner_id, **kwargs):
    with app.app_context():
        item = Item(description="Seeded", user_id=owner_id, status="Available", **kwargs)
        db.session.add(item)
        db.session.commit()
        return item.id


def test_create_item(app, client, user):
    response = client.post("/api/v1/items", headers=_auth(client), json={
        "description": "New bike",
        "link": "https://example.com/bike",
        "price": 250.0,
        "category": "Sports",
        "quantity": 1,
    })

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["description"] == "New bike"
    assert item["user_id"] == user
    assert "status" not in item  # own item — surprise protection


def test_create_item_validation_errors(client, user):
    response = client.post("/api/v1/items", headers=_auth(client), json={
        "description": "", "link": "notaurl",
    })
    assert response.status_code == 400
    assert len(response.get_json()["errors"]) >= 1


def test_patch_own_item(app, client, user):
    item_id = _make_item(app, user)
    response = client.patch(f"/api/v1/items/{item_id}", headers=_auth(client),
                            json={"description": "Renamed", "price": 9.5})
    assert response.status_code == 200
    assert response.get_json()["item"]["description"] == "Renamed"


def test_patch_rejects_non_owner(app, client, user, other_user):
    item_id = _make_item(app, other_user)
    response = client.patch(f"/api/v1/items/{item_id}", headers=_auth(client),
                            json={"description": "Hijacked"})
    assert response.status_code == 403


def test_delete_own_item_and_404_after(app, client, user):
    item_id = _make_item(app, user)
    headers = _auth(client)
    assert client.delete(f"/api/v1/items/{item_id}", headers=headers).status_code == 200
    assert client.delete(f"/api/v1/items/{item_id}", headers=headers).status_code == 404


def test_delete_rejects_non_owner(app, client, user, other_user):
    item_id = _make_item(app, other_user)
    assert client.delete(f"/api/v1/items/{item_id}", headers=_auth(client)).status_code == 403


def test_claim_then_unclaim(app, client, user, other_user):
    item_id = _make_item(app, other_user)
    headers = _auth(client)

    claimed = client.post(f"/api/v1/items/{item_id}/claim", headers=headers)
    assert claimed.status_code == 200
    assert claimed.get_json()["item"]["status"] == "Claimed"

    unclaimed = client.post(f"/api/v1/items/{item_id}/unclaim", headers=headers)
    assert unclaimed.get_json()["item"]["status"] == "Available"


def test_claim_own_item_conflict(app, client, user):
    item_id = _make_item(app, user)
    response = client.post(f"/api/v1/items/{item_id}/claim", headers=_auth(client))
    assert response.status_code == 409
    assert response.get_json()["error"] == "own_item"


def test_purchase(app, client, user, other_user):
    item_id = _make_item(app, other_user)
    response = client.post(f"/api/v1/items/{item_id}/purchase", headers=_auth(client))
    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "Purchased"
