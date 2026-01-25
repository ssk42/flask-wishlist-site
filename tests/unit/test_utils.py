"""Tests for utility functions."""


class TestGetItemsUrlWithFilters:
    """Tests for get_items_url_with_filters helper."""

    def test_no_filters(self, app, client):
        """Should return base items URL with no filters."""
        from services.utils import get_items_url_with_filters

        with client.session_transaction() as sess:
            # Clear any existing filters
            sess.clear()

        with app.test_request_context():
            url = get_items_url_with_filters()
            assert url == '/items'

    def test_user_filter(self, app, client):
        """Should include user filter in URL."""
        from services.utils import get_items_url_with_filters

        with client.session_transaction() as sess:
            sess['user_filter'] = '1'

        with client.application.test_request_context():
            from flask import session
            session['user_filter'] = '1'
            url = get_items_url_with_filters()
            assert 'user_filter=1' in url

    def test_status_filter(self, app, client):
        """Should include status filter in URL."""
        from services.utils import get_items_url_with_filters

        with client.application.test_request_context():
            from flask import session
            session['status_filter'] = 'Available'
            url = get_items_url_with_filters()
            assert 'status_filter=Available' in url

    def test_priority_filter(self, app, client):
        """Should include priority filter in URL."""
        from services.utils import get_items_url_with_filters

        with client.application.test_request_context():
            from flask import session
            session['priority_filter'] = 'High'
            url = get_items_url_with_filters()
            assert 'priority_filter=High' in url

    def test_event_filter(self, app, client):
        """Should include event filter in URL."""
        from services.utils import get_items_url_with_filters

        with client.application.test_request_context():
            from flask import session
            session['event_filter'] = '5'
            url = get_items_url_with_filters()
            assert 'event_filter=5' in url

    def test_search_query(self, app, client):
        """Should include search query in URL."""
        from services.utils import get_items_url_with_filters

        with client.application.test_request_context():
            from flask import session
            session['q'] = 'nintendo'
            url = get_items_url_with_filters()
            assert 'q=nintendo' in url

    def test_sort_options(self, app, client):
        """Should include sort options in URL."""
        from services.utils import get_items_url_with_filters

        with client.application.test_request_context():
            from flask import session
            session['sort_by'] = 'price'
            session['sort_order'] = 'desc'
            url = get_items_url_with_filters()
            assert 'sort_by=price' in url
            assert 'sort_order=desc' in url

    def test_multiple_filters(self, app, client):
        """Should include multiple filters in URL."""
        from services.utils import get_items_url_with_filters

        with client.application.test_request_context():
            from flask import session
            session['user_filter'] = '2'
            session['status_filter'] = 'Claimed'
            session['priority_filter'] = 'Medium'
            url = get_items_url_with_filters()
            assert 'user_filter=2' in url
            assert 'status_filter=Claimed' in url
            assert 'priority_filter=Medium' in url
