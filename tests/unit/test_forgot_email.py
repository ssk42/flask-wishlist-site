"""Tests for forgot email functionality."""
from models import User, db


def test_forgot_email_page_loads(client):
    """Test that the forgot email page loads successfully."""
    response = client.get("/forgot_email")
    assert response.status_code == 200
    assert b"Forgot your email?" in response.data
    assert b"Find My Email" in response.data


def test_forgot_email_finds_exact_match(client, app):
    """Test that forgot email finds a user with exact name match."""
    with app.app_context():
        # Create a test user
        user = User(name="John Doe", email="john.doe@example.com")
        db.session.add(user)
        db.session.commit()

        # Try to find email by name
        response = client.post(
            "/forgot_email",
            data={"name": "John Doe"},
            follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Found your account!" in response.data
        assert b"john.doe@example.com" in response.data


def test_forgot_email_case_insensitive(client, app):
    """Test that forgot email search is case-insensitive."""
    with app.app_context():
        # Create a test user
        user = User(name="Jane Smith", email="jane.smith@example.com")
        db.session.add(user)
        db.session.commit()

        # Try with different case
        response = client.post(
            "/forgot_email",
            data={"name": "jane smith"},
            follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Found your account!" in response.data
        assert b"jane.smith@example.com" in response.data


def test_forgot_email_not_found(client):
    """Test that forgot email shows error when user not found."""
    response = client.post(
        "/forgot_email",
        data={"name": "Nonexistent User"},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"We could not find an account with that name" in response.data


def test_forgot_email_empty_name(client):
    """Test that forgot email shows error when name is empty."""
    response = client.post(
        "/forgot_email",
        data={"name": ""},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Please enter your name" in response.data


def test_forgot_email_strips_whitespace(client, app):
    """Test that forgot email strips whitespace from input."""
    with app.app_context():
        # Create a test user
        user = User(name="Bob Wilson", email="bob.wilson@example.com")
        db.session.add(user)
        db.session.commit()

        # Try with extra whitespace
        response = client.post(
            "/forgot_email",
            data={"name": "  Bob Wilson  "},
            follow_redirects=True
        )

        assert response.status_code == 200
        assert b"Found your account!" in response.data
        assert b"bob.wilson@example.com" in response.data


def test_login_page_has_forgot_email_link(client):
    """Test that login page has a link to forgot email."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Forgot your email?" in response.data
    assert b'href="/forgot_email"' in response.data
