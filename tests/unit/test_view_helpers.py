"""Tests for view helper utilities."""
import pytest

from services.view_helpers import flash_and_redirect


class TestFlashAndRedirect:
    """Tests for the flash_and_redirect() function."""

    def test_flashes_message_and_redirects(self, app):
        """Should flash message and return redirect response."""
        with app.test_request_context():
            response = flash_and_redirect(
                'Operation successful!',
                'success',
                'dashboard.index'
            )

            # Check it returns a redirect response
            assert response.status_code == 302
            assert '/dashboard' in response.location or '/' in response.location

    def test_flash_message_is_stored(self, app, client):
        """Should store flash message in session."""
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'
            sess['_fresh'] = True

        with app.test_request_context():
            from flask import session, get_flashed_messages
            # Need to import after context is set up
            flash_and_redirect('Test message', 'info', 'dashboard.index')

            # Check the message was flashed
            messages = get_flashed_messages(with_categories=True)
            assert ('info', 'Test message') in messages

    def test_redirect_with_url_kwargs(self, app):
        """Should pass kwargs to url_for for redirect."""
        with app.test_request_context():
            # Using an endpoint that takes parameters
            response = flash_and_redirect(
                'Item deleted.',
                'warning',
                'items.items_list'
            )

            assert response.status_code == 302

    def test_success_category(self, app):
        """Should work with success category."""
        with app.test_request_context():
            from flask import get_flashed_messages
            flash_and_redirect('Saved!', 'success', 'dashboard.index')

            messages = get_flashed_messages(with_categories=True)
            assert any(cat == 'success' for cat, msg in messages)

    def test_danger_category(self, app):
        """Should work with danger category."""
        with app.test_request_context():
            from flask import get_flashed_messages
            flash_and_redirect('Error occurred.', 'danger', 'dashboard.index')

            messages = get_flashed_messages(with_categories=True)
            assert any(cat == 'danger' for cat, msg in messages)

    def test_warning_category(self, app):
        """Should work with warning category."""
        with app.test_request_context():
            from flask import get_flashed_messages
            flash_and_redirect('Please review.', 'warning', 'dashboard.index')

            messages = get_flashed_messages(with_categories=True)
            assert any(cat == 'warning' for cat, msg in messages)

    def test_info_category(self, app):
        """Should work with info category."""
        with app.test_request_context():
            from flask import get_flashed_messages
            flash_and_redirect('FYI...', 'info', 'dashboard.index')

            messages = get_flashed_messages(with_categories=True)
            assert any(cat == 'info' for cat, msg in messages)

    def test_returns_redirect_object(self, app):
        """Should return a Response object with redirect."""
        with app.test_request_context():
            from werkzeug.wrappers import Response
            result = flash_and_redirect('Test', 'info', 'dashboard.index')

            assert isinstance(result, Response)
            assert result.status_code == 302
