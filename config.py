"""
Configuration management for the Wishlist application.
Supports multiple environments: development, testing, production.
"""

import os
from dotenv import load_dotenv

# Application constants
PRIORITY_CHOICES = ['High', 'Medium', 'Low']
STATUS_CHOICES = ['Available', 'Claimed', 'Purchased', 'Received', 'Splitting']

# Load environment variables from .env file (skip if in pytest to allow test overrides)
if 'pytest' not in os.getenv('_', '').lower():
    load_dotenv()


class Config:
    """Base configuration class with common settings."""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FAMILY_PASSWORD = os.getenv('FAMILY_PASSWORD', 'wishlist2025')

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database Connection Pooling (Item 13)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }

    # CSRF Protection
    WTF_CSRF_TIME_LIMIT = None  # CSRF tokens don't expire
    WTF_CSRF_ENABLED = True

    # Session
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Database
    @staticmethod
    def get_database_uri():
        """Get database URI with postgres:// to postgresql:// conversion for Heroku."""
        uri = os.getenv('DATABASE_URL')
        if uri:
            # Heroku uses postgres://, SQLAlchemy requires postgresql://
            if uri.startswith('postgres://'):
                uri = uri.replace('postgres://', 'postgresql://', 1)
            return uri
        return None

    SQLALCHEMY_DATABASE_URI = get_database_uri.__func__() or 'sqlite:///wishlist.db'

    # Redis (for future caching)
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Caching (Item 12)
    CACHE_TYPE = 'RedisCache' if os.getenv('REDIS_URL') else 'SimpleCache'
    CACHE_REDIS_URL = os.getenv('REDIS_URL')
    CACHE_DEFAULT_TIMEOUT = 300

    # Rate Limiting
    @staticmethod
    def get_ratelimit_storage_uri():
        """Get rate limit storage URI, defaulting to Heroku Redis if available."""
        uri = os.getenv('RATELIMIT_STORAGE_URI') or os.getenv('REDIS_TLS_URL') or os.getenv('REDIS_URL') or 'memory://'
        
        # Heroku Redis uses self-signed certificates, so we must ignore validition
        if uri and uri.startswith('rediss://') and 'ssl_cert_reqs' not in uri:
            if '?' in uri:
                uri += '&ssl_cert_reqs=none'
            else:
                uri += '?ssl_cert_reqs=none'
        
        return uri

    RATELIMIT_STORAGE_URI = get_ratelimit_storage_uri.__func__()

    # Email (for future notifications)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@wishlist.app')
    
    # Sentry
    SENTRY_DSN = os.getenv('SENTRY_DSN')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'wishlist.log')

    # Security Headers (configured in app.py)
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
    }


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True
    TESTING = False

    # Use SQLite for local development if no DATABASE_URL provided
    if not os.getenv('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = 'sqlite:///wishlist.db'


class TestingConfig(Config):
    """Testing environment configuration."""

    TESTING = True
    DEBUG = True

    # Use in-memory SQLite for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Simpler pool settings for testing
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }
    
    # Disable Rate Limiting for testing
    RATELIMIT_ENABLED = False
    
    # Use SimpleCache (memory) for tests
    CACHE_TYPE = 'SimpleCache'
    CACHE_REDIS_URL = None


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False

    # Enforce HTTPS cookies in production
    SESSION_COOKIE_SECURE = True

    # Stricter security headers for production
    SECURITY_HEADERS = {
        **Config.SECURITY_HEADERS,
        'Content-Security-Policy': "default-src 'self'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' https://cdn.jsdelivr.net; img-src 'self' data: https:;",
    }


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}


def get_config():
    """Get configuration based on FLASK_ENV environment variable."""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
