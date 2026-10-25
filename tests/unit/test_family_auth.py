"""Web auth tests — name-only login, no family code (changed 2026-10-25).

The family code still gates the iOS API login (see test_api_v1_auth.py);
the website login/registration intentionally require only a name (+ email
at registration) to keep sign-in simple.
"""

import pytest
from models import db, User


def test_register_success(client, app):
    # @spec AUTH-FLOW-001, AUTH-FLOW-002
    """Registration needs only a name and email — no family code."""
    response = client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Registration successful" in response.data

    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.name == 'Test User'


def test_register_duplicate_name_rejected(client, app):
    # @spec AUTH-FLOW-001
    """A second account with the same name (any capitalization) is rejected."""
    with app.app_context():
        db.session.add(User(name='Taken Name', email='first@example.com'))
        db.session.commit()

    response = client.post('/register', data={
        'name': 'taken name',
        'email': 'second@example.com',
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"already in use" in response.data

    with app.app_context():
        assert User.query.filter_by(email='second@example.com').first() is None


def test_login_success_by_name(client, app):
    # @spec AUTH-FLOW-001, AUTH-FLOW-002
    """Login with just the account name."""
    with app.app_context():
        db.session.add(User(name='Existing User', email='existing@example.com'))
        db.session.commit()

    response = client.post('/login', data={
        'name': 'Existing User',
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome back, Existing User!" in response.data


def test_login_name_is_case_and_whitespace_insensitive(client, app):
    # @spec AUTH-FLOW-002
    """Typing '  existing user ' still signs in as Existing User."""
    with app.app_context():
        db.session.add(User(name='Existing User', email='existing@example.com'))
        db.session.commit()

    response = client.post('/login', data={
        'name': '  existing user ',
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome back, Existing User!" in response.data


def test_login_unknown_name_rejected(client, app):
    # @spec AUTH-FLOW-003
    """Login with a name that has no account is rejected."""
    with app.app_context():
        db.session.add(User(name='Target User', email='target@example.com'))
        db.session.commit()

    response = client.post('/login', data={
        'name': 'No Such Person',
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"could not find an account with that name" in response.data
    assert b"Welcome back, Target User" not in response.data
