"""API-level surprise protection: an item's claim status must be invisible to
its owner but visible to other users."""

from models import db, Item


def _auth(client, email="test@example.com"):
    response = client.post("/api/v1/auth/login",
                           json={"email": email, "family_code": "testsecret"})
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def test_claim_status_hidden_from_owner_visible_to_others(client, app, user, other_user):
    """A giver's claim is absent from the owner's view but present for others."""

    # Create an item owned by `user` (fixtures return int ids).
    with app.app_context():
        item = Item(description="Secret Gift", user_id=user, status="Available")
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # Another user (giver) claims it.
    claim = client.post(f"/api/v1/items/{item_id}/claim", headers=_auth(client, "other@example.com"))
    assert claim.status_code == 200
    assert claim.get_json()["item"]["status"] == "Claimed"

    # The owner's view must omit the claim status entirely (not nulled — absent).
    owner_items = client.get("/api/v1/items", headers=_auth(client)).get_json()["items"]
    owner_item = next(i for i in owner_items if i["id"] == item_id)
    assert "status" not in owner_item, "Owner must not see claim status"
    assert "last_updated_by" not in owner_item, "Owner must not see who claimed"

    # A third user's view shows the claim and the claimer.
    other_list = client.get("/api/v1/items", headers=_auth(client, "other@example.com"))
    other_item = next(i for i in other_list.get_json()["items"] if i["id"] == item_id)
    assert other_item["status"] == "Claimed"
    assert other_item["last_updated_by"]["id"] == other_user, \
        "Claimer must be visible to other givers"
