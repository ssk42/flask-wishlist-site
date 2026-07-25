"""Tests for ApiToken and Device models."""

from models import db, ApiToken, Device


def test_api_token_defaults(app, user):
    with app.app_context():
        token = ApiToken(user_id=user, token_hash="a" * 64)
        db.session.add(token)
        db.session.commit()

        assert token.id is not None
        assert token.revoked is False
        assert token.created_at is not None
        assert token.last_used_at is None
        assert token.user.id == user


def test_device_defaults(app, user):
    with app.app_context():
        device = Device(user_id=user, apns_token="deadbeef")
        db.session.add(device)
        db.session.commit()

        assert device.id is not None
        assert device.platform == "ios"
        assert device.created_at is not None
        assert device.user.id == user
