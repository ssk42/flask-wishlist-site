"""Tests that /api/v1 framework-level errors (404/405/429/etc.) return the
JSON error envelope documented in docs/API_V1.md, while non-API paths keep
their existing HTML error pages."""

from services.api_auth import issue_token


def _auth_headers(user):
    token = issue_token(user)
    return {"Authorization": f"Bearer {token}"}


def test_wrong_method_on_api_v1_route_returns_json_405(client):
    # /api/v1/auth/login is POST-only.
    response = client.get("/api/v1/auth/login")
    assert response.status_code == 405
    assert response.get_json() == {"error": "method_not_allowed"}


def test_unknown_api_v1_path_returns_json_404(client, user):
    headers = _auth_headers(user)
    response = client.get("/api/v1/does-not-exist", headers=headers)
    assert response.status_code == 404
    assert response.get_json() == {"error": "not_found"}


def test_web_404_still_returns_html(client):
    # Non-/api/v1 paths must keep the existing HTML error page behavior.
    response = client.get("/nonexistent-web-page")
    assert response.status_code == 404
    assert "text/html" in response.content_type
    assert b"Page Not Found" in response.data


def test_429_handler_returns_json_for_api_v1_path(app):
    """RATELIMIT_ENABLED is False in TestingConfig, so we cannot trigger a
    real 429 through the limiter in the unit suite. Instead, verify the
    registered 429 error handler produces the JSON envelope by invoking it
    directly within a request context whose path starts with /api/v1."""
    from werkzeug.exceptions import TooManyRequests

    handler = app.error_handler_spec[None][429][TooManyRequests]
    with app.test_request_context("/api/v1/auth/login"):
        response = handler(TooManyRequests())
    # Handler may return a (body, status) tuple or a Response.
    if isinstance(response, tuple):
        body, status = response
        assert status == 429
        assert body.get_json() == {"error": "rate_limited"}
    else:
        assert response.status_code == 429
        assert response.get_json() == {"error": "rate_limited"}
