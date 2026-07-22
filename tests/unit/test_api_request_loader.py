"""Tests for Bearer-token authentication via the Flask-Login request_loader."""

from services.api_auth import issue_token


def _bearer(app, user_id):
    with app.app_context():
        return {"Authorization": f"Bearer {issue_token(user_id)}"}


def test_bearer_token_authenticates_existing_route(app, client, user):
    response = client.get("/items", headers=_bearer(app, user))
    assert response.status_code == 200


def test_bad_bearer_token_still_redirects_web_route(client, user):
    response = client.get("/items", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_no_header_keeps_existing_behavior(client):
    response = client.get("/items")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
