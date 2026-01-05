"""Redis caching layer for price crawler."""
import hashlib
import logging
from flask import current_app
from extensions import cache

logger = logging.getLogger(__name__)

# Cache TTL in seconds (1 hour)
CACHE_TTL = 3600

def get_cached_response(url):
    """Retrieve cached HTML content for a URL if available."""
    try:
        if not url:
            return None
            
        cache_key = _make_cache_key(url)
        content = cache.get(cache_key)
        
        if content:
            logger.debug(f"Cache HIT for {url}")
            return content
            
        logger.debug(f"Cache MISS for {url}")
        return None
        
    except Exception as e:
        logger.warning(f"Cache retrieval failed: {e}")
        return None

def cache_response(url, content):
    """Cache the HTML content for a URL."""
    try:
        if not url or not content:
            return
            
        cache_key = _make_cache_key(url)
        cache.set(cache_key, content, timeout=CACHE_TTL)
        logger.debug(f"Cached content for {url}")
        
    except Exception as e:
        logger.warning(f"Cache storage failed: {e}")

def _make_cache_key(url):
    """Generate a consistent cache key for a URL."""
    # Use MD5 of URL to ensure safe key characters and fixed length
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    return f"price:html:{url_hash}"
