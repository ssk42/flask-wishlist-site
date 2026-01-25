
from unittest.mock import patch


def login_via_post(client, email):
    return client.post(
        "/login",
        data={
            "email": email,
            "password": "testsecret"},
        follow_redirects=True)


def test_fetch_metadata_requires_login(client):
    response = client.post(
        "/api/fetch-metadata",
        json={
            "url": "https://example.com"})
    # Flask-Login redirects to /login, so we expect 302 Found
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_fetch_metadata_missing_url(client, login):
    response = client.post("/api/fetch-metadata", json={})
    assert response.status_code == 400
    assert response.json == {'error': 'Missing URL'}


@patch('services.price_service.fetch_metadata')
def test_fetch_metadata_success(mock_fetch, client, login):
    # Setup mock return value
    mock_data = {
        'title': 'Test Item',
        'price': 100.0,
        'image_url': 'http://example.com/image.jpg',
        'domain': 'example.com'
    }
    mock_fetch.return_value = mock_data

    # Make request
    response = client.post("/api/fetch-metadata",
                           json={"url": "https://example.com/product"})

    # Assertions
    assert response.status_code == 200
    assert response.json == mock_data
    mock_fetch.assert_called_once_with("https://example.com/product")


@patch('services.price_service.fetch_metadata')
def test_fetch_metadata_failure(mock_fetch, client, login):
    # Setup mock to raise exception
    mock_fetch.side_effect = Exception("Connection error")

    # Make request
    response = client.post("/api/fetch-metadata",
                           json={"url": "https://example.com/fail"})

    # Assertions
    assert response.status_code == 500
    assert response.json == {'error': 'Connection error'}
