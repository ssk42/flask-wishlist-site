"""Tests for API v1 device registration."""

from models import db, Device


def _auth(client, email="test@example.com"):
    response = client.post("/api/v1/auth/login",
                           json={"email": email, "family_code": "testsecret"})
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def test_register_device(app, client, user):
    response = client.post("/api/v1/devices", headers=_auth(client),
                           json={"apns_token": "abc123", "platform": "ios"})
    assert response.status_code == 201
    with app.app_context():
        device = Device.query.one()
        assert device.apns_token == "abc123"
        assert device.user_id == user


def test_register_device_reassigns_existing_token(app, client, user, other_user):
    with app.app_context():
        db.session.add(Device(user_id=other_user, apns_token="shared-phone"))
        db.session.commit()

    client.post("/api/v1/devices", headers=_auth(client),
                json={"apns_token": "shared-phone"})

    with app.app_context():
        assert Device.query.one().user_id == user


def test_register_device_requires_token(client, user):
    response = client.post("/api/v1/devices", headers=_auth(client), json={})
    assert response.status_code == 400


def test_delete_device(app, client, user):
    headers = _auth(client)
    client.post("/api/v1/devices", headers=headers, json={"apns_token": "abc123"})

    assert client.delete("/api/v1/devices/abc123", headers=headers).status_code == 200
    with app.app_context():
        assert Device.query.count() == 0
