"""Flask application factory and configuration."""

import os
import logging
import click
from flask import Flask, render_template
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_compress import Compress
from whitenoise import WhiteNoise
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from extensions import limiter, cache
from config import get_config

# Import db and models from models.py
from models import db, User, Event, Item, Notification


def create_app(config_name=None):
    """Application factory for creating Flask app instances."""
    # Initialize Sentry before app creation
    if os.getenv('SENTRY_DSN'):
        sentry_sdk.init(
            dsn=os.getenv('SENTRY_DSN'),
            integrations=[
                FlaskIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            environment=os.getenv('FLASK_ENV', 'development')
        )

    app = Flask(__name__)

    # Setup logging
    try:
        from services.logging_config import setup_logging
        setup_logging(app)
    except ImportError:
        logging.basicConfig(level=logging.INFO)
        app.logger.info('Using basic logging configuration')

    # Load configuration
    app.config.from_object(get_config())

    # Database configuration override (handle Heroku/Env vars dynamically)
    uri = os.getenv("DATABASE_URL")
    if uri:
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        os.environ['DATABASE_URL'] = uri
        app.config['SQLALCHEMY_DATABASE_URI'] = uri

    # Ensure instance folder exists for SQLite
    if app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite'):
        try:
            os.makedirs(app.instance_path)
        except OSError:
            pass

    # Security headers (now loaded from config, just applying them)
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses."""
        headers = app.config.get('SECURITY_HEADERS', {})
        for header, value in headers.items():
            response.headers[header] = value
        return response

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    CSRFProtect(app)
    Mail(app)
    Compress(app)
    # Configure Limiter (storage options configured via RATELIMIT_STORAGE_URI
    # in config)
    limiter.init_app(app)

    # Initialize caching
    cache.init_app(app)

    # Initialize WhiteNoise for static files
    app.wsgi_app = WhiteNoise(app.wsgi_app, root='static/')

    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from blueprints import (
        auth_bp, api_bp, dashboard_bp, events_bp, social_bp, items_bp
    )
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(items_bp)

    # Context processors
    @app.context_processor
    def inject_notifications():
        """Inject unread notification count into all templates."""
        if current_user.is_authenticated:
            return dict(unread_notifications_count=current_user.unread_count)
        return dict(unread_notifications_count=0)

    @app.context_processor
    def inject_claimed_count():
        """Inject the count of claimed items for navbar badge."""
        if current_user.is_authenticated:
            claimed_count = Item.query.filter(
                Item.last_updated_by_id == current_user.id,
                Item.status == 'Claimed',
                Item.user_id != current_user.id
            ).count()
            return {'nav_claimed_count': claimed_count}
        return {'nav_claimed_count': 0}

    # Global Error Handlers

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        # Explicit capture for Sentry as requested
        if os.getenv('SENTRY_DSN'):
            sentry_sdk.capture_exception(error)
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    # CLI commands
    @app.cli.command('send-reminders')
    def send_reminders_command():
        """Send event reminder emails for events happening in 7 days."""
        from services.tasks import send_event_reminders
        click.echo('Sending event reminders...')
        stats = send_event_reminders(app, db, Event, Item, User)
        click.echo(f'Events processed: {stats["events_processed"]}')
        click.echo(f'Emails sent: {stats["emails_sent"]}')
        click.echo(f'Errors: {stats["errors"]}')
        if stats['errors'] > 0:
            raise SystemExit(1)

    @app.cli.command('update-prices')
    @click.option('--force', is_flag=True,
                  help='Force update all items regardless of last update time')
    def update_prices_command(force):
        """Update prices for items not updated in 7 days."""
        from services.price_service import update_stale_prices
        if force:
            click.echo('Force updating ALL prices (ignoring 7-day window)...')
        else:
            click.echo('Updating stale prices...')
        stats = update_stale_prices(
            app, db, Item, Notification, force_all=force)
        click.echo(f'Items processed: {stats["items_processed"]}')
        click.echo(f'Prices updated: {stats["prices_updated"]}')
        click.echo(f'Price drops detected: {stats["price_drops"]}')
        click.echo(f'Errors: {stats["errors"]}')

    return app


# Create app instance for backwards compatibility
app = create_app()


if __name__ == '__main__':
    app.run()  # pragma: no cover
