"""Tests for the API token service."""

import hashlib

from models import db, ApiToken
from services.api_auth import issue_token, resolve_token, revoke_token


def test_issue_token_stores_only_hash(app, user):
    with app.app_context():
        plaintext = issue_token(user)

        assert len(plaintext) >= 32
        row = ApiToken.query.one()
        assert row.token_hash == hashlib.sha256(plaintext.encode()).hexdigest()
        assert row.token_hash != plaintext


def test_resolve_token_returns_user_and_touches_last_used(app, user):
    with app.app_context():
        plaintext = issue_token(user)

        resolved = resolve_token(plaintext)

        assert resolved is not None
        assert resolved.id == user
        assert ApiToken.query.one().last_used_at is not None


def test_resolve_token_rejects_garbage_and_empty(app, user):
    with app.app_context():
        issue_token(user)

        assert resolve_token("not-a-real-token") is None
        assert resolve_token("") is None
        assert resolve_token(None) is None


def test_revoked_token_no_longer_resolves(app, user):
    with app.app_context():
        plaintext = issue_token(user)

        assert revoke_token(plaintext) is True
        assert resolve_token(plaintext) is None
        assert revoke_token(plaintext) is False  # already revoked
