"""Tests for API v1 notifications and metadata endpoints."""

from models import db, Notification


def _auth(client, email="test@example.com"):
    response = client.post("/api/v1/auth/login",
                           json={"email": email, "family_code": "testsecret"})
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def _seed_notifications(app, user, other_user):
    with app.app_context():
        db.session.add_all([
            Notification(user_id=user, message="mine 1", link="/items"),
            Notification(user_id=user, message="mine 2", link="/items"),
            Notification(user_id=other_user, message="theirs", link="/items"),
        ])
        db.session.commit()
        return [n.id for n in Notification.query.filter_by(user_id=user).all()]


def test_list_notifications_scoped_to_current_user(app, client, user, other_user):
    _seed_notifications(app, user, other_user)
    response = client.get("/api/v1/notifications", headers=_auth(client))

    body = response.get_json()
    assert {n["message"] for n in body["notifications"]} == {"mine 1", "mine 2"}
    assert body["unread_count"] == 2


def test_mark_one_read_and_cannot_touch_others(app, client, user, other_user):
    mine = _seed_notifications(app, user, other_user)
    headers = _auth(client)

    assert client.post(f"/api/v1/notifications/{mine[0]}/read", headers=headers).status_code == 200

    with app.app_context():
        theirs = Notification.query.filter_by(user_id=other_user).first()
    assert client.post(f"/api/v1/notifications/{theirs.id}/read", headers=headers).status_code == 404


def test_read_all(app, client, user, other_user):
    _seed_notifications(app, user, other_user)
    headers = _auth(client)

    client.post("/api/v1/notifications/read-all", headers=headers)

    body = client.get("/api/v1/notifications", headers=headers).get_json()
    assert body["unread_count"] == 0


def test_metadata_endpoint(client, user, monkeypatch):
    import services.price_service as price_service
    monkeypatch.setattr(price_service, "fetch_metadata",
                        lambda url: {"title": "Widget", "price": 9.99, "image": None})
    # The SSRF guard resolves hostnames via DNS; stub it so unit tests stay offline.
    import blueprints.api_v1 as api_v1
    monkeypatch.setattr(api_v1, "_is_public_http_url", lambda url: True)

    response = client.post("/api/v1/metadata", headers=_auth(client),
                           json={"url": "https://example.com/widget"})

    assert response.status_code == 200
    assert response.get_json()["title"] == "Widget"


def test_metadata_requires_url(client, user):
    response = client.post("/api/v1/metadata", headers=_auth(client), json={})
    assert response.status_code == 400


def test_metadata_rejects_non_public_urls(client, user):
    """SSRF guard: local/private/non-http targets are refused before any fetch."""
    headers = _auth(client)
    for url in [
        "http://localhost:8000/admin",        # loopback via hostname
        "http://127.0.0.1/latest",            # loopback literal
        "http://192.168.1.10/router",         # RFC1918
        "http://169.254.169.254/meta-data",   # link-local / cloud metadata
        "ftp://example.com/file",             # non-http scheme
        "not a url",
    ]:
        response = client.post("/api/v1/metadata", headers=headers, json={"url": url})
        assert response.status_code == 400, url
        assert response.get_json()["error"] == "invalid_url", url
