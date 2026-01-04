"""Flask blueprints for the Wishlist application."""

from .auth import bp as auth_bp
from .api import bp as api_bp
from .dashboard import bp as dashboard_bp
from .events import bp as events_bp
from .social import bp as social_bp
from .items import bp as items_bp

__all__ = [
    'auth_bp',
    'api_bp',
    'dashboard_bp',
    'events_bp',
    'social_bp',
    'items_bp',
]
