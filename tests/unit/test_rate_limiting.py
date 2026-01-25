
import pytest
from app import create_app
from extensions import limiter


@pytest.fixture
def rate_limit_app():
    """Create an app with enabled rate limiting for testing."""
    app = create_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False

    # Enable rate limiting for testing
    limiter.enabled = True

    with app.app_context():
        yield app

    # Reset
    limiter.enabled = False
    limiter.reset()


def test_login_rate_limit(rate_limit_app):
    """Test that login endpoint is rate limited."""
    client = rate_limit_app.test_client()

    # Hit the endpoint 5 times (allowed)
    for _ in range(5):
        response = client.get('/login')
        assert response.status_code == 200

    # The 6th time should be blocked
    response = client.get('/login')
    assert response.status_code == 429
    assert b"Too Many Requests" in response.data


def test_register_rate_limit(rate_limit_app):
    """Test that register endpoint is rate limited."""
    client = rate_limit_app.test_client()

    # Hit the endpoint 5 times (allowed)
    for _ in range(5):
        response = client.get('/register')
        assert response.status_code == 200

    # The 6th time should be blocked
    response = client.get('/register')
    assert response.status_code == 429
    assert b"Too Many Requests" in response.data
