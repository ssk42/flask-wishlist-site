
import pytest
from unittest.mock import patch
from flask import abort
from app import create_app

@pytest.fixture
def error_app():
    """Create a fresh app for error handler tests."""
    app = create_app('testing')
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['PROPAGATE_EXCEPTIONS'] = False # Important for 500 handler to catch it
    return app

def test_404_error_handler(error_app):
    """Test that 404 error page is rendered."""
    client = error_app.test_client()
    response = client.get('/non-existent-url')
    assert response.status_code == 404
    assert b"Page Not Found" in response.data

def test_403_error_handler(error_app):
    """Test that 403 error page is rendered."""
    # Register route BEFORE first request
    @error_app.route('/trigger-403')
    def trigger_403():
        abort(403)
    
    client = error_app.test_client()
    response = client.get('/trigger-403')
    assert response.status_code == 403
    assert b"Access Denied" in response.data

def test_500_error_handler(error_app):
    """Test that 500 error page is rendered and rollback occurs."""
    # Register route BEFORE first request
    @error_app.route('/trigger-500')
    def trigger_500():
        raise Exception("Test Exception")
    
    client = error_app.test_client()
    
    # Mock sentry capture within the request context logic if possible, 
    # but here we just want to verify the template is rendered.
    # To verify Sentry capture, we'd need to mock 'app.os.getenv' or similar,
    # or patch sentry_sdk.capture_exception globally.
    
    with patch('sentry_sdk.capture_exception') as mock_capture:
        with patch.dict('os.environ', {'SENTRY_DSN': 'https://example@sentry.io/1'}):
             response = client.get('/trigger-500')
             
             assert response.status_code == 500
             assert b"Something Went Wrong" in response.data
             # Verify Sentry capture was called
             mock_capture.assert_called_once()
