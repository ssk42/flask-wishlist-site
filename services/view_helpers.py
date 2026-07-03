"""View helper utilities for reducing boilerplate in blueprints."""

from flask import flash, redirect, url_for


def flash_and_redirect(message, category, endpoint, **kwargs):
    """Flash a message and redirect to an endpoint.

    This helper combines the common pattern of flashing a message and
    redirecting, reducing code duplication across blueprints.

    Args:
        message: The flash message to display
        category: Flash category ('success', 'danger', 'warning', 'info')
        endpoint: The endpoint to redirect to
        **kwargs: Additional arguments passed to url_for()

    Returns:
        A redirect response

    Example:
        return flash_and_redirect('Item deleted.', 'info', 'items.items_list')
        return flash_and_redirect('Login successful!', 'success', 'dashboard.index')
    """
    flash(message, category)
    return redirect(url_for(endpoint, **kwargs))
