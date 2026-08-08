"""Token-based authentication for the JSON API (v1).

Plaintext tokens are returned to the client exactly once at login;
only SHA-256 hashes are persisted, so a database leak cannot be
replayed as credentials.
"""

import datetime
import hashlib
import secrets

from models import db, ApiToken


def _hash_token(plaintext):
    return hashlib.sha256(plaintext.encode()).hexdigest()


def issue_token(user_id):
    """Create a token for user_id and return the plaintext (shown once)."""
    plaintext = secrets.token_urlsafe(32)
    db.session.add(ApiToken(user_id=user_id, token_hash=_hash_token(plaintext)))
    db.session.commit()
    return plaintext


def resolve_token(plaintext):
    """Return the User for a valid, unrevoked token, else None."""
    if not plaintext:
        return None
    token = ApiToken.query.filter_by(token_hash=_hash_token(plaintext), revoked=False).first()
    if token is None:
        return None
    token.last_used_at = datetime.datetime.now(datetime.timezone.utc)
    db.session.commit()
    return token.user


def revoke_token(plaintext):
    """Revoke a token. Returns True if a live token was revoked."""
    if not plaintext:
        return False
    token = ApiToken.query.filter_by(token_hash=_hash_token(plaintext), revoked=False).first()
    if token is None:
        return False
    token.revoked = True
    db.session.commit()
    return True
