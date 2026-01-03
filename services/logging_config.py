"""
Logging configuration for the Wishlist application.
Provides structured logging with different outputs for development and production.
"""

import logging
import logging.config
import os
try:
    from pythonjsonlogger.json import JsonFormatter
except ImportError:
    from pythonjsonlogger import jsonlogger
    JsonFormatter = jsonlogger.JsonFormatter


class CustomJsonFormatter(JsonFormatter):
    """Custom JSON formatter to add consistent fields to all log records."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['app'] = 'wishlist'
        log_record['environment'] = os.getenv('FLASK_ENV', 'development')
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id


def get_logging_config(log_level=None, log_file=None):
    """
    Get logging configuration dictionary.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for development, path for production)

    Returns:
        dict: Logging configuration dictionary
    """
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO')

    if log_file is None:
        log_file = os.getenv('LOG_FILE', 'wishlist.log')

    is_development = os.getenv('FLASK_ENV', 'development') == 'development'

    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            },
            'json': {
                '()': 'services.logging_config.CustomJsonFormatter',
                'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'default' if is_development else 'json',
                'stream': 'ext://sys.stdout',
            },
        },
        'root': {
            'level': log_level,
            'handlers': ['console'],
        },
        'loggers': {
            'werkzeug': {
                'level': 'INFO',
            },
            'sqlalchemy.engine': {
                'level': 'WARNING',  # Set to INFO to see SQL queries
            },
        },
    }

    # Add file handler in production
    if not is_development and log_file:
        config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'json',
            'filename': log_file,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
        }
        config['root']['handlers'].append('file')

    return config


def setup_logging(app=None):
    """
    Setup logging for the application.

    Args:
        app: Flask application instance (optional)
    """
    config = get_logging_config()
    logging.config.dictConfig(config)

    logger = logging.getLogger(__name__)
    logger.info('Logging configured successfully')

    if app:
        # Flask's logger will use our configuration
        app.logger.setLevel(logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO')))
        app.logger.info('Flask logging configured')

    return logger
