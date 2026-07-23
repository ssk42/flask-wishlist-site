"""Tests for /api/v1 auth endpoints and the blueprint-wide auth gate."""


def _login(client, email="test@example.com", code="testsecret"):
    return client.post("/api/v1/auth/login", json={"email": email, "family_code": code})


def test_login_success_returns_token_and_user(client, user):
    response = _login(client)

    assert response.status_code == 200
    body = response.get_json()
    assert len(body["token"]) >= 32
    assert body["user"]["email"] == "test@example.com"
    assert body["user"]["id"] == user


def test_login_wrong_family_code(client, user):
    response = _login(client, code="wrong")
    assert response.status_code == 401
    assert response.get_json()["error"] == "invalid_family_code"


def test_login_empty_family_code_rejected(client, user):
    """An empty supplied family_code must never authenticate."""
    response = _login(client, code="")
    assert response.status_code == 401
    assert response.get_json()["error"] == "invalid_family_code"


def test_login_empty_configured_family_password_never_authenticates(app, client, user):
    """Regression guard: if FAMILY_PASSWORD is unset/empty,
    hmac.compare_digest(b'', b'') is True, so an empty supplied code must
    still be rejected rather than silently authenticating any known email."""
    original = app.config.get("FAMILY_PASSWORD")
    app.config["FAMILY_PASSWORD"] = ""
    try:
        response = _login(client, code="")
        assert response.status_code == 401
        assert response.get_json()["error"] == "invalid_family_code"
    finally:
        app.config["FAMILY_PASSWORD"] = original


def test_login_unknown_email(client, user):
    response = _login(client, email="ghost@example.com")
    assert response.status_code == 401
    assert response.get_json()["error"] == "unknown_email"


def test_protected_route_returns_json_401_without_token(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401
    assert response.get_json() == {"error": "unauthorized"}


def test_logout_revokes_token(client, user):
    token = _login(client).get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    # Token no longer works
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 401
