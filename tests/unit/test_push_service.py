"""Tests for the APNs push service (transport always mocked)."""

from models import db, Device, Notification
from services import push_service
from services.notification_service import create_notification


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class FakeClient:
    """Stands in for httpx.Client; records posts, returns scripted statuses."""

    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.posts = []

    def post(self, url, headers=None, json=None):
        self.posts.append({"url": url, "headers": headers, "json": json})
        return FakeResponse(self.statuses.pop(0))


APNS_CONFIG = {
    "APNS_KEY_ID": "KEY123",
    "APNS_TEAM_ID": "TEAM123",
    # A throwaway EC key is generated in the test to satisfy ES256 signing.
    "APNS_BUNDLE_ID": "com.example.wishlist",
    "APNS_USE_SANDBOX": True,
}


def _enable_apns(app):
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    app.config.update(APNS_CONFIG, APNS_KEY_P8=pem)


def test_push_disabled_without_config(app, user):
    with app.app_context():
        app.config.update(APNS_KEY_P8=None)
        assert push_service.apns_enabled() is False
        assert push_service.send_push_to_user(user, "hello") == 0


def test_push_sends_to_each_device(app, user):
    with app.app_context():
        _enable_apns(app)
        db.session.add_all([
            Device(user_id=user, apns_token="tok1"),
            Device(user_id=user, apns_token="tok2"),
        ])
        db.session.commit()
        client = FakeClient([200, 200])

        sent = push_service.send_push_to_user(user, "You got a gift", link="/items/1",
                                              client=client)

        assert sent == 2
        assert "tok1" in client.posts[0]["url"]
        assert client.posts[0]["json"]["aps"]["alert"]["body"] == "You got a gift"
        assert client.posts[0]["headers"]["apns-topic"] == "com.example.wishlist"
        assert "sandbox" in client.posts[0]["url"]


def test_gone_device_is_deleted(app, user):
    with app.app_context():
        _enable_apns(app)
        db.session.add(Device(user_id=user, apns_token="stale"))
        db.session.commit()

        sent = push_service.send_push_to_user(user, "hi", client=FakeClient([410]))

        assert sent == 0
        assert Device.query.count() == 0


def test_create_notification_survives_missing_celery(app, user):
    """The Notification row must be written even if push enqueue fails."""
    with app.app_context():
        _enable_apns(app)  # enabled, so the enqueue path is exercised
        notif = create_notification(user, "You have a comment", "/items")

        assert notif.id is not None
        assert Notification.query.count() == 1
