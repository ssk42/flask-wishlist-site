"""Session-based filter management for persisting view state."""

from flask import session, request


class SessionFilterManager:
    """Manages filter persistence in Flask session for list views.

    This class extracts the filter logic from items_list() to provide
    reusable filter persistence across page navigation.

    Filter keys managed:
        - user_filter: Filter by user ID
        - status_filter: Filter by item status
        - priority_filter: Filter by priority level
        - event_filter: Filter by event ID
        - q: Search query string
        - sort_by: Sort column name
        - sort_order: 'asc' or 'desc'

    Example usage:
        fm = SessionFilterManager(request)
        if fm.should_clear():
            fm.clear_all()
            return redirect(url_for('items.items_list'))

        filters = fm.get_filters()
        # Use filters['user_filter'], filters['status_filter'], etc.
    """

    FILTER_KEYS = [
        'user_filter', 'status_filter', 'priority_filter',
        'event_filter', 'q', 'sort_by', 'sort_order'
    ]

    DEFAULT_SORT_BY = 'priority'
    DEFAULT_SORT_ORDER = 'asc'

    def __init__(self, request_obj=None):
        """Initialize with Flask request object.

        Args:
            request_obj: Flask request object (defaults to current request)
        """
        self.request = request_obj or request

    def should_clear(self):
        """Check if filters should be cleared based on request args."""
        return self.request.args.get('clear_filters') == 'true'

    def clear_all(self):
        """Clear all filter values from session."""
        for key in self.FILTER_KEYS:
            session.pop(key, None)

    def has_new_filters(self):
        """Check if request contains new filter values.

        Only truthy (non-empty) values count, matching the original inline
        logic: a present-but-empty param (e.g. ``?status_filter=``) must not
        trigger a session save that would wipe existing filters.
        """
        return any(
            self.request.args.get(key)
            for key in self.FILTER_KEYS
        )

    def save_from_request(self):
        """Save filter values from request args to session."""
        session['user_filter'] = self.request.args.get('user_filter', type=int)
        session['status_filter'] = self.request.args.get('status_filter')
        session['priority_filter'] = self.request.args.get('priority_filter')
        session['event_filter'] = self.request.args.get('event_filter', type=int)
        session['q'] = self.request.args.get('q', '').strip()
        session['sort_by'] = self.request.args.get('sort_by', self.DEFAULT_SORT_BY)
        session['sort_order'] = self.request.args.get('sort_order', self.DEFAULT_SORT_ORDER)

    def get_filters(self):
        """Get current filter values, from request or session.

        If new filters are provided in request args, saves them to session
        and returns those values. Otherwise returns values from session.

        Returns:
            Dictionary with all filter keys and their current values.
        """
        if self.has_new_filters():
            self.save_from_request()

        return {
            'user_filter': session.get('user_filter'),
            'status_filter': session.get('status_filter'),
            'priority_filter': session.get('priority_filter'),
            'event_filter': session.get('event_filter'),
            'q': session.get('q', ''),
            'sort_by': session.get('sort_by', self.DEFAULT_SORT_BY),
            'sort_order': session.get('sort_order', self.DEFAULT_SORT_ORDER)
        }
