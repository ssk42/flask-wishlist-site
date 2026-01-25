"""Extensions registry.

All extensions here are initialized in app.py or by the blueprints.
"""
import os
import redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache

limiter = Limiter(key_func=get_remote_address)
cache = Cache()

# Redis client for identity management and other features
# Handles both regular redis:// and secure rediss:// URLs
_redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
if _redis_url:
    try:
        redis_client = redis.from_url(_redis_url)
    except Exception:
        redis_client = None
else:
    redis_client = None
