"""Tests for API v1 read endpoints: users, items, my-claims."""

from models import db, Item


def _auth(client, email="test@example.com"):
    response = client.post("/api/v1/auth/login",
                           json={"email": email, "family_code": "testsecret"})
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def _seed(app, user, other_user):
    with app.app_context():
        db.session.add_all([
            Item(description="Own available", user_id=user, status="Available"),
            Item(description="Own claimed secretly", user_id=user, status="Claimed",
                 last_updated_by_id=other_user),
            Item(description="Their gadget", user_id=other_user, status="Available",
                 category="Tech"),
            Item(description="Their claimed book", user_id=other_user, status="Claimed",
                 last_updated_by_id=user),
        ])
        db.session.commit()


def test_users_lists_family_with_item_counts(app, client, user, other_user):
    _seed(app, user, other_user)
    response = client.get("/api/v1/users", headers=_auth(client))

    assert response.status_code == 200
    users = {u["name"]: u for u in response.get_json()["users"]}
    assert users["Test User"]["item_count"] == 2
    assert users["Other User"]["item_count"] == 2


def test_items_hides_own_claim_status(app, client, user, other_user):
    _seed(app, user, other_user)
    response = client.get("/api/v1/items", headers=_auth(client))

    items = {i["description"]: i for i in response.get_json()["items"]}
    assert len(items) == 4
    # own items: no status key at all
    assert "status" not in items["Own claimed secretly"]
    assert "status" not in items["Own available"]
    # others' items: status visible
    assert items["Their claimed book"]["status"] == "Claimed"


def test_status_filter_excludes_viewers_own_items(app, client, user, other_user):
    """Filtering by status must not reveal own-item status by inclusion."""
    _seed(app, user, other_user)
    response = client.get("/api/v1/items?status=Claimed", headers=_auth(client))

    descriptions = [i["description"] for i in response.get_json()["items"]]
    assert descriptions == ["Their claimed book"]


def test_items_filters_user_category_and_search(app, client, user, other_user):
    _seed(app, user, other_user)
    headers = _auth(client)

    by_user = client.get(f"/api/v1/items?user_id={other_user}", headers=headers)
    assert len(by_user.get_json()["items"]) == 2

    by_category = client.get("/api/v1/items?category=Tech", headers=headers)
    assert [i["description"] for i in by_category.get_json()["items"]] == ["Their gadget"]

    by_search = client.get("/api/v1/items?q=gadget", headers=headers)
    assert [i["description"] for i in by_search.get_json()["items"]] == ["Their gadget"]


def test_my_claims(app, client, user, other_user):
    _seed(app, user, other_user)
    response = client.get("/api/v1/my-claims", headers=_auth(client))

    items = response.get_json()["items"]
    assert [i["description"] for i in items] == ["Their claimed book"]
    assert items[0]["status"] == "Claimed"
