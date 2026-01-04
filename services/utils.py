"""Shared utility functions for the Wishlist application."""

from flask import session, url_for


def get_items_url_with_filters():
    """
    Build items URL with preserved filters from session.

    This helper maintains filter state across page navigation,
    allowing users to return to their filtered view after
    performing actions like adding, editing, or claiming items.

    Returns:
        str: URL for the items list with current filter parameters
    """
    filters = {}

    # User filter
    if session.get('user_filter'):
        filters['user_filter'] = session['user_filter']

    # Status filter
    if session.get('status_filter'):
        filters['status_filter'] = session['status_filter']

    # Priority filter
    if session.get('priority_filter'):
        filters['priority_filter'] = session['priority_filter']

    # Event filter
    if session.get('event_filter'):
        filters['event_filter'] = session['event_filter']

    # Search query
    if session.get('q'):
        filters['q'] = session['q']

    # Sort options
    if session.get('sort_by'):
        filters['sort_by'] = session['sort_by']
    if session.get('sort_order'):
        filters['sort_order'] = session['sort_order']

    # Use blueprint-qualified endpoint name
    return url_for('items.items_list', **filters)
