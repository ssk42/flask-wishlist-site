"""Tests for SessionFilterManager class."""
import pytest

from services.session_filter_manager import SessionFilterManager


class TestSessionFilterManagerInit:
    """Tests for SessionFilterManager initialization."""

    def test_init_with_request_object(self, app):
        """Should accept a request object."""
        with app.test_request_context('/?user_filter=1'):
            from flask import request
            fm = SessionFilterManager(request)
            assert fm.request is request

    def test_init_without_request_uses_current(self, app):
        """Should use current request if none provided."""
        with app.test_request_context('/?status_filter=Available'):
            fm = SessionFilterManager()
            # Should have access to current request
            assert fm.request.args.get('status_filter') == 'Available'

    def test_filter_keys_defined(self):
        """Should have all expected filter keys."""
        expected_keys = [
            'user_filter', 'status_filter', 'priority_filter',
            'event_filter', 'q', 'sort_by', 'sort_order'
        ]
        assert SessionFilterManager.FILTER_KEYS == expected_keys

    def test_default_sort_values(self):
        """Should have correct default sort values."""
        assert SessionFilterManager.DEFAULT_SORT_BY == 'priority'
        assert SessionFilterManager.DEFAULT_SORT_ORDER == 'asc'


class TestShouldClear:
    """Tests for the should_clear() method."""

    def test_should_clear_true_when_param_is_true(self, app):
        """Should return True when clear_filters=true."""
        with app.test_request_context('/?clear_filters=true'):
            fm = SessionFilterManager()
            assert fm.should_clear() is True

    def test_should_clear_false_when_param_is_false(self, app):
        """Should return False when clear_filters has other value."""
        with app.test_request_context('/?clear_filters=false'):
            fm = SessionFilterManager()
            assert fm.should_clear() is False

    def test_should_clear_false_when_param_missing(self, app):
        """Should return False when clear_filters not present."""
        with app.test_request_context('/'):
            fm = SessionFilterManager()
            assert fm.should_clear() is False


class TestClearAll:
    """Tests for the clear_all() method."""

    def test_clear_all_removes_all_filter_keys(self, app, client):
        """Should remove all filter keys from session."""
        with client.session_transaction() as sess:
            sess['user_filter'] = 1
            sess['status_filter'] = 'Available'
            sess['priority_filter'] = 'High'
            sess['event_filter'] = 5
            sess['q'] = 'laptop'
            sess['sort_by'] = 'price'
            sess['sort_order'] = 'desc'
            sess['other_key'] = 'preserved'

        with client.application.test_request_context():
            from flask import session
            # Manually copy session data to current context
            session['user_filter'] = 1
            session['status_filter'] = 'Available'
            session['other_key'] = 'preserved'

            fm = SessionFilterManager()
            fm.clear_all()

            # Filter keys should be cleared
            assert session.get('user_filter') is None
            assert session.get('status_filter') is None
            assert session.get('priority_filter') is None
            # Other keys should be preserved
            assert session.get('other_key') == 'preserved'

    def test_clear_all_on_empty_session(self, app):
        """Should not raise error when session has no filters."""
        with app.test_request_context():
            fm = SessionFilterManager()
            fm.clear_all()  # Should not raise


class TestHasNewFilters:
    """Tests for the has_new_filters() method."""

    def test_has_new_filters_true_with_user_filter(self, app):
        """Should return True when user_filter in request args."""
        with app.test_request_context('/?user_filter=1'):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is True

    def test_has_new_filters_true_with_status_filter(self, app):
        """Should return True when status_filter in request args."""
        with app.test_request_context('/?status_filter=Available'):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is True

    def test_has_new_filters_true_with_priority_filter(self, app):
        """Should return True when priority_filter in request args."""
        with app.test_request_context('/?priority_filter=High'):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is True

    def test_has_new_filters_true_with_event_filter(self, app):
        """Should return True when event_filter in request args."""
        with app.test_request_context('/?event_filter=5'):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is True

    def test_has_new_filters_true_with_search_query(self, app):
        """Should return True when q in request args."""
        with app.test_request_context('/?q=laptop'):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is True

    def test_has_new_filters_true_with_sort_by(self, app):
        """Should return True when sort_by in request args."""
        with app.test_request_context('/?sort_by=price'):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is True

    def test_has_new_filters_true_with_sort_order(self, app):
        """Should return True when sort_order in request args."""
        with app.test_request_context('/?sort_order=desc'):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is True

    def test_has_new_filters_false_with_no_filters(self, app):
        """Should return False when no filter params in request."""
        with app.test_request_context('/'):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is False

    def test_has_new_filters_false_with_other_params(self, app):
        """Should return False when only non-filter params present."""
        with app.test_request_context('/?page=2&foo=bar'):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is False

    def test_has_new_filters_true_with_multiple_filters(self, app):
        """Should return True when multiple filters in request."""
        with app.test_request_context('/?user_filter=1&status_filter=Available'):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is True

    def test_has_new_filters_false_with_empty_param(self, app):
        """A present-but-empty param must NOT count as a new filter."""
        with app.test_request_context('/?status_filter='):
            fm = SessionFilterManager()
            assert fm.has_new_filters() is False

    def test_empty_param_does_not_wipe_session_filters(self, app):
        """Regression: ?status_filter= (empty) must not overwrite session filters."""
        with app.test_request_context('/?status_filter='):
            from flask import session
            # Pre-populate session with active filters
            session['user_filter'] = 1
            session['priority_filter'] = 'High'
            session['sort_by'] = 'price'
            session['sort_order'] = 'desc'

            fm = SessionFilterManager()
            filters = fm.get_filters()

            # Pre-existing session filters must survive
            assert session.get('user_filter') == 1
            assert session.get('priority_filter') == 'High'
            assert session.get('sort_by') == 'price'
            assert session.get('sort_order') == 'desc'
            assert filters['user_filter'] == 1
            assert filters['priority_filter'] == 'High'
            assert filters['sort_by'] == 'price'
            assert filters['sort_order'] == 'desc'

    def test_truthy_param_does_trigger_save(self, app):
        """Companion: ?status_filter=Available (truthy) DOES trigger the save."""
        with app.test_request_context('/?status_filter=Available'):
            from flask import session
            # Pre-populate session with active filters
            session['user_filter'] = 1
            session['priority_filter'] = 'High'

            fm = SessionFilterManager()
            filters = fm.get_filters()

            # Save was triggered: new value stored, absent params reset
            assert session.get('status_filter') == 'Available'
            assert filters['status_filter'] == 'Available'
            assert session.get('user_filter') is None
            assert session.get('priority_filter') is None


class TestSaveFromRequest:
    """Tests for the save_from_request() method."""

    def test_save_user_filter_as_int(self, app):
        """Should save user_filter as integer."""
        with app.test_request_context('/?user_filter=5'):
            from flask import session
            fm = SessionFilterManager()
            fm.save_from_request()
            assert session.get('user_filter') == 5

    def test_save_status_filter(self, app):
        """Should save status_filter as string."""
        with app.test_request_context('/?status_filter=Claimed'):
            from flask import session
            fm = SessionFilterManager()
            fm.save_from_request()
            assert session.get('status_filter') == 'Claimed'

    def test_save_priority_filter(self, app):
        """Should save priority_filter as string."""
        with app.test_request_context('/?priority_filter=High'):
            from flask import session
            fm = SessionFilterManager()
            fm.save_from_request()
            assert session.get('priority_filter') == 'High'

    def test_save_event_filter_as_int(self, app):
        """Should save event_filter as integer."""
        with app.test_request_context('/?event_filter=10'):
            from flask import session
            fm = SessionFilterManager()
            fm.save_from_request()
            assert session.get('event_filter') == 10

    def test_save_search_query_strips_whitespace(self, app):
        """Should save q with whitespace stripped."""
        with app.test_request_context('/?q=  laptop  '):
            from flask import session
            fm = SessionFilterManager()
            fm.save_from_request()
            assert session.get('q') == 'laptop'

    def test_save_sort_by_with_default(self, app):
        """Should save sort_by with default value."""
        with app.test_request_context('/'):
            from flask import session
            fm = SessionFilterManager()
            fm.save_from_request()
            assert session.get('sort_by') == 'priority'

    def test_save_sort_order_with_default(self, app):
        """Should save sort_order with default value."""
        with app.test_request_context('/'):
            from flask import session
            fm = SessionFilterManager()
            fm.save_from_request()
            assert session.get('sort_order') == 'asc'

    def test_save_custom_sort_options(self, app):
        """Should save custom sort options."""
        with app.test_request_context('/?sort_by=price&sort_order=desc'):
            from flask import session
            fm = SessionFilterManager()
            fm.save_from_request()
            assert session.get('sort_by') == 'price'
            assert session.get('sort_order') == 'desc'


class TestGetFilters:
    """Tests for the get_filters() method."""

    def test_get_filters_from_request_when_new(self, app):
        """Should get filters from request when new filters present."""
        with app.test_request_context('/?user_filter=3&status_filter=Available'):
            fm = SessionFilterManager()
            filters = fm.get_filters()
            assert filters['user_filter'] == 3
            assert filters['status_filter'] == 'Available'

    def test_get_filters_from_session_when_no_new(self, app):
        """Should get filters from session when no new filters in request."""
        with app.test_request_context('/'):
            from flask import session
            session['user_filter'] = 2
            session['status_filter'] = 'Claimed'

            fm = SessionFilterManager()
            filters = fm.get_filters()
            assert filters['user_filter'] == 2
            assert filters['status_filter'] == 'Claimed'

    def test_get_filters_returns_all_keys(self, app):
        """Should return all filter keys in result."""
        with app.test_request_context('/'):
            fm = SessionFilterManager()
            filters = fm.get_filters()

            expected_keys = ['user_filter', 'status_filter', 'priority_filter',
                             'event_filter', 'q', 'sort_by', 'sort_order']
            for key in expected_keys:
                assert key in filters

    def test_get_filters_default_sort_values(self, app):
        """Should return default sort values when not set."""
        with app.test_request_context('/'):
            fm = SessionFilterManager()
            filters = fm.get_filters()
            assert filters['sort_by'] == 'priority'
            assert filters['sort_order'] == 'asc'

    def test_get_filters_default_q_empty_string(self, app):
        """Should return empty string for q when not set."""
        with app.test_request_context('/'):
            fm = SessionFilterManager()
            filters = fm.get_filters()
            assert filters['q'] == ''

    def test_get_filters_saves_to_session(self, app):
        """Should save new filters to session."""
        with app.test_request_context('/?priority_filter=Medium'):
            from flask import session
            fm = SessionFilterManager()
            fm.get_filters()
            assert session.get('priority_filter') == 'Medium'


class TestIntegration:
    """Integration tests for SessionFilterManager."""

    def test_filter_persistence_flow(self, app, client):
        """Should persist filters across multiple requests."""
        # First request with filters
        with app.test_request_context('/?user_filter=1&priority_filter=High'):
            from flask import session
            fm = SessionFilterManager()
            filters = fm.get_filters()
            assert filters['user_filter'] == 1
            assert filters['priority_filter'] == 'High'

            # Filters should be in session now
            assert session.get('user_filter') == 1
            assert session.get('priority_filter') == 'High'

    def test_clear_filters_flow(self, app):
        """Should clear filters when clear_filters=true."""
        with app.test_request_context('/?clear_filters=true'):
            from flask import session
            # Pre-populate session
            session['user_filter'] = 1
            session['status_filter'] = 'Available'

            fm = SessionFilterManager()
            if fm.should_clear():
                fm.clear_all()

            assert session.get('user_filter') is None
            assert session.get('status_filter') is None

    def test_new_filters_override_session(self, app):
        """New request filters should override session values."""
        with app.test_request_context('/?status_filter=Claimed'):
            from flask import session
            # Pre-populate session with different value
            session['status_filter'] = 'Available'
            session['user_filter'] = 1

            fm = SessionFilterManager()
            filters = fm.get_filters()

            # New value from request should be used
            assert filters['status_filter'] == 'Claimed'
            # Session value should be updated
            assert session.get('status_filter') == 'Claimed'
