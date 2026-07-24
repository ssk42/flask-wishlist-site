"""Price fetching service for wishlist items."""
import datetime
import logging
import random
import time
from urllib.parse import urlparse
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from config import Config
from services import price_cache, price_metrics
from services.price_extraction.extractors import (
    get_extractor_for_url,
    AmazonPriceExtractor,
    GenericPriceExtractor,
    TargetPriceExtractor,
)

logger = logging.getLogger(__name__)

# Feature flag for stealth extraction (from config/environment)
AMAZON_STEALTH_ENABLED = Config.AMAZON_STEALTH_ENABLED

# Singleton identity manager (lazy initialized)
_identity_manager = None


def _get_identity_manager():
    """Get or create the identity manager singleton."""
    global _identity_manager
    if _identity_manager is None:
        try:
            from extensions import redis_client
            from services.amazon_stealth import IdentityManager
            _identity_manager = IdentityManager(redis_client)
        except Exception as e:
            logger.warning(f"Could not initialize IdentityManager: {e}")
            return None
    return _identity_manager


# Rotating user agents to reduce blocking
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# Rate limiting: minimum seconds between requests
RATE_LIMIT_SECONDS = 2

# Request timeout in seconds
REQUEST_TIMEOUT = 15

# Max retries for failed requests
MAX_RETRIES = 2


def _get_session():
    """Create a requests session with random user agent."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    })
    return session




class CachedResponse:
    """Mock response object for cached content."""
    def __init__(self, text, status_code=200):
        self.text = text
        self.content = text.encode('utf-8')
        self.status_code = status_code
        self.ok = True
        self.url = ""
        
    def raise_for_status(self):
        pass

def _make_request(url, session=None, retries=MAX_RETRIES):
    """Make a request with retry logic and caching."""
    # Check cache first
    cached_text = price_cache.get_cached_response(url)
    if cached_text:
        resp = CachedResponse(cached_text)
        resp.url = url
        return resp

    if session is None:
        session = _get_session()

    for attempt in range(retries + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            
            # Cache successful responses (if text content)
            if response.ok and response.text:
                price_cache.cache_response(url, response.text)
                
            return response
        except requests.RequestException as e:
            if attempt < retries:
                wait_time = (attempt + 1) * 2 + random.uniform(0, 1)
                logger.info(f'Retry {attempt + 1}/{retries} for {url} after {wait_time:.1f}s')
                time.sleep(wait_time)
                # Get a fresh session with new user agent
                session = _get_session()
            else:
                logger.warning(f'All retries failed for {url}: {str(e)}')
                # Don't raise, return None so callers can handle or try fallback
                return None
    return None


def fetch_price(url):
    """Fetch the current price from a product URL."""
    if not url:
        return None

    start_time = time.time()
    success = False
    price = None
    error_type = None

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Amazon and Target need special fetching (stealth / Playwright fallback);
        # everything else is fetch-then-extract with the registry.
        if 'amazon' in domain or domain in ['a.co', 'amzn.to', 'amzn.eu']:
            price = _fetch_amazon_price(url)
        elif 'target.com' in domain:
            price = _fetch_target_price(url)
        else:
            price = _fetch_standard_price(url)

        if price is not None:
            success = True

        return price

    except Exception as e:
        error_type = str(e)
        logger.warning(f'Failed to fetch price from {url}: {str(e)}')
        return None
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        price_metrics.log_extraction_attempt(
            url=url, 
            success=success, 
            price=price, 
            error_type=error_type,
            response_time_ms=duration_ms
        )


def fetch_metadata(url):
    """Fetch metadata (title, price, image, etc.) from a URL.

    Args:
        url: The product URL

    Returns:
        Dictionary with keys: title, price, image_url, category, domain
    """
    if not url:
        return {}

    metadata = {
        'title': None,
        'price': None,
        'image_url': None,
        'description': None,
        'url': url
    }

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        metadata['domain'] = domain

        # Site-specific extractors
        if 'amazon' in domain or domain in ['a.co', 'amzn.to', 'amzn.eu']:
            data = _fetch_amazon_metadata(url)
            if data:
                metadata.update(data)
            return metadata
        
        # Generic approach for other sites
        data = _fetch_generic_metadata(url)
        if data:
            metadata.update(data)
        return metadata

    except Exception as e:
        logger.warning(f'Failed to fetch metadata from {url}: {str(e)}')
        return metadata


def _fetch_with_playwright(url):
    """Fetch content using Playwright (headless browser) for stubborn sites."""
    # Check cache first
    cached_text = price_cache.get_cached_response(url)
    if cached_text:
        return BeautifulSoup(cached_text, 'html.parser')

    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Create a context with realistic browser attributes
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800},
                device_scale_factor=2,
            )
            page = context.new_page()
            
            # Stealthier navigation
            try:
                page.goto(url, timeout=30000, wait_until='domcontentloaded')
                # Wait a bit for JS to execute (many sites render price via JS)
                page.wait_for_timeout(2000)
                
                content = page.content()
                
                # Cache the content
                if content:
                    price_cache.cache_response(url, content)

                soup = BeautifulSoup(content, 'html.parser')
                return soup
            finally:
                browser.close()
                
    except Exception as e:
        logger.error(f"Playwright fetch failed for {url}: {e}")
        return None



def _fetch_standard_price(url):
    """Fetch a page and extract its price with the site-appropriate extractor."""
    try:
        response = _make_request(url)
        if not response:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        return get_extractor_for_url(url).extract_from_soup(soup)
    except Exception as e:
        logger.warning(f'Price fetch failed for {url}: {str(e)}')
        return None


def _fetch_amazon_price(url):
    """Fetch price from Amazon product page.

    Uses stealth extraction when AMAZON_STEALTH_ENABLED is True and identity
    manager is available. Falls back to legacy extraction otherwise.

    Note: Amazon actively blocks scraping. Stealth mode uses browser fingerprinting
    rotation to improve success rates.
    """
    # Try stealth extraction if enabled
    if AMAZON_STEALTH_ENABLED:
        manager = _get_identity_manager()
        if manager:
            identity = manager.get_healthy_identity()
            if identity:
                try:
                    from services.amazon_stealth import (
                        stealth_fetch_amazon_sync,
                        AmazonFailureType,
                    )

                    result = stealth_fetch_amazon_sync(url, identity, manager)

                    if result.success:
                        manager.mark_success(identity)
                        return result.price
                    elif result.failure_type == AmazonFailureType.CAPTCHA:
                        manager.mark_burned(identity)
                        logger.warning(f"Stealth extraction hit CAPTCHA for {url}, identity burned")
                        return None
                    else:
                        # Other failures (no price found, rate limited, etc.)
                        logger.warning(f"Stealth extraction failed ({result.failure_type}): {url}")
                        return None
                except Exception as e:
                    logger.error(f"Stealth extraction error for {url}: {e}")
                    # Fall through to legacy on unexpected errors
            else:
                logger.warning(f"All Amazon identities burned, skipping: {url}")
                return None

    # Fall back to legacy extraction
    return _fetch_amazon_price_legacy(url)


def _fetch_amazon_price_legacy(url):
    """Legacy Amazon extraction: requests first, Playwright on CAPTCHA.

    Note: Amazon actively blocks scraping. This may fail due to CAPTCHAs,
    bot detection, or page structure changes. For reliable Amazon pricing,
    consider the Amazon Product Advertising API.
    """
    try:
        session = _get_session()
        session.headers.update({
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.amazon.com/',
            'DNT': '1',
        })

        response = _make_request(url, session)
        if not response:
            logger.warning(f'Amazon request failed (possible bot detection): {url}')
            return None

        extractor = AmazonPriceExtractor()
        if 'captcha' in response.text.lower() or 'robot check' in response.text.lower():
            logger.warning(f'Amazon returned CAPTCHA/robot check page via requests, trying Playwright: {url}')
            soup = _fetch_with_playwright(url)
            if soup:
                return extractor.extract_from_soup(soup)
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        return extractor.extract_from_soup(soup)
    except Exception as e:
        logger.warning(f'Amazon price fetch failed for {url}: {str(e)}')
        return None


def _fetch_target_price(url):
    """Fetch price from Target, falling back to Playwright for JS-rendered pages."""
    extractor = TargetPriceExtractor()
    try:
        response = _make_request(url)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title and soup.title.string else ''
            if 'Access Denied' in title:
                logger.warning(f'Target blocked requests for {url}')
            else:
                price = extractor.extract_from_soup(soup)
                if price:
                    return price

        logger.info(f'Trying Target fallback via Playwright for {url}')
        soup = _fetch_with_playwright(url)
        if soup:
            return extractor.extract_from_soup(soup)
        return None
    except Exception as e:
        logger.warning(f'Target price fetch failed for {url}: {str(e)}')
        return None


def _fetch_amazon_metadata(url):
    """Fetch all metadata from Amazon."""
    try:
        session = _get_session()
        session.headers.update({
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.amazon.com/',
            'DNT': '1',
        })
        response = _make_request(url, session)

        if response and 'captcha' not in response.text.lower() and 'robot check' not in response.text.lower():
            soup = BeautifulSoup(response.text, 'html.parser')
        else:
            logger.warning(f'Amazon CAPTCHA detected, switching to Playwright for metadata: {url}')
            soup = _fetch_with_playwright(url)

        if not soup:
            return {}

        data = AmazonPriceExtractor().extract_metadata(soup)
        # The extractor uses 'image'; the public fetch_metadata() contract uses 'image_url'.
        metadata = {}
        if data.get('title'):
            metadata['title'] = data['title']
        if data.get('price'):
            metadata['price'] = data['price']
        if data.get('image'):
            metadata['image_url'] = data['image']
        return metadata

    except Exception as e:
        logger.warning(f'Error fetching Amazon metadata: {e}')
        return {}


def _fetch_generic_metadata(url):
    """Fetch metadata using OpenGraph and generic extractors."""
    metadata = {}
    try:
        response = _make_request(url)
        if not response:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. OpenGraph Tags
        og_mapping = {
            'og:title': 'title',
            'og:image': 'image_url',
            'og:description': 'description',
            'og:price:amount': 'price',
            'product:price:amount': 'price'
        }
        
        for prop, key in og_mapping.items():
            elem = soup.find('meta', property=prop)
            if elem and elem.get('content'):
                val = elem['content']
                if key == 'price':
                    price = GenericPriceExtractor.parse_price(val)
                    if price:
                        metadata[key] = price
                else:
                    metadata[key] = val

        # 2. Title fallback
        if not metadata.get('title'):
            if soup.title:
                metadata['title'] = soup.title.get_text(strip=True)

        # 3. Price Fallback
        if not metadata.get('price'):
            price = GenericPriceExtractor().extract_from_soup(soup)
            if price:
                metadata['price'] = price

        # 4. Image Fallback
        if not metadata.get('image_url'):
            elem = soup.find('meta', attrs={'name': 'twitter:image'})
            if elem and elem.get('content'):
                metadata['image_url'] = elem['content']

        return metadata

    except Exception as e:
        logger.warning(f"Error fetching generic metadata: {e}")
        return None


def update_stale_prices(app, db, Item, Notification=None, force_all=False):
    """Update prices for items that haven't been updated in 7 days.

    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
        Item: Item model class
        Notification: Notification model class (optional, for price drop alerts)
        force_all: If True, update all items with links regardless of last update time

    Returns:
        Dictionary with counts of items processed, updated, and errors
    """
    with app.app_context():
        seven_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)

        # Diagnostic: count items with links
        total_items = Item.query.count()
        items_with_links = Item.query.filter(
            Item.link.isnot(None),
            Item.link != ''
        ).count()
        items_never_updated = Item.query.filter(
            Item.link.isnot(None),
            Item.link != '',
            Item.price_updated_at.is_(None)
        ).count()
        items_stale = Item.query.filter(
            Item.link.isnot(None),
            Item.link != '',
            Item.price_updated_at < seven_days_ago
        ).count()

        logger.info(f'Price update diagnostics: total_items={total_items}, items_with_links={items_with_links}, '
                    f'never_updated={items_never_updated}, stale={items_stale}, cutoff_date={seven_days_ago}, force_all={force_all}')

        # Find items with links that need updating
        # Find items with links that need updating
        items = get_items_needing_update(Item, db, seven_days_ago, force_all)

        stats = {
            'items_processed': 0,
            'prices_updated': 0,
            'price_drops': 0,
            'errors': 0
        }

        if not items:
            logger.info('No items to update')
            return stats

        # Collect URLs mapped to items (handle duplicates if any, though unlikely to fetch same URL twice ideally)
        url_to_items = defaultdict(list)
        for item in items:
            if item.link:
                url_to_items[item.link].append(item)
        
        urls = list(url_to_items.keys())
        logger.info(f"Starting async batch update for {len(urls)} URLs")

        try:
            from services import price_async
            from services.price_history import record_price_history
            import asyncio
            
            # Run async fetch
            results = asyncio.run(price_async.fetch_prices_batch(urls))
            
            # Process results
            for url, new_price in results.items():
                items_for_url = url_to_items.get(url, [])
                
                for item in items_for_url:
                    stats['items_processed'] += 1
                    
                    if new_price is not None:
                        old_price = item.price
                        item.price = new_price
                        item.price_updated_at = datetime.datetime.now(datetime.timezone.utc)
                        
                        # Record history
                        record_price_history(item.id, new_price, source='auto')
                        
                        if old_price != new_price:
                             stats['prices_updated'] += 1
                             # Check for significant price drop (≥10%)
                             if Notification and old_price and new_price < old_price:
                                drop_percent = ((old_price - new_price) / old_price) * 100
                                if drop_percent >= 10:
                                    stats['price_drops'] += 1
                                    _create_price_drop_notifications(
                                        item, old_price, new_price, drop_percent, db, Notification
                                    )
                    else:
                        # Update timestamp to avoid repeatedly trying failed URLs immediately (set to now)
                        item.price_updated_at = datetime.datetime.now(datetime.timezone.utc)
            
            # Commit all changes
            db.session.commit()
            
            # Handle items that failed (not in results)
            # Use timestamp update so we don't retry them immediately next run
            failed_urls = set(urls) - set(results.keys())
            if failed_urls:
                for url in failed_urls:
                    for item in url_to_items[url]:
                        item.price_updated_at = datetime.datetime.now(datetime.timezone.utc)
                db.session.commit()
                stats['errors'] += len(failed_urls)
                
        except Exception as e:
            logger.error(f"Batch update failed: {e}")
            db.session.rollback()
            stats['errors'] += len(items)

        logger.info(f'Price update complete: {stats}')
        return stats


def _create_price_drop_notifications(item, old_price, new_price, drop_percent, db, Notification):
    """Create notifications for significant price drops.
    
    Notifies:
    - Item owner
    - User who claimed the item (if any, and not the owner)
    """
    from services.notification_service import create_notification

    # Notification for owner
    owner_message = f"🎉 Price drop! '{item.description[:50]}' is now ${new_price:.2f} (was ${old_price:.2f}) - {drop_percent:.0f}% off!"
    create_notification(item.user_id, owner_message, f"/items?user_filter={item.user_id}")
    logger.info(f'Created price drop notification for owner (user_id={item.user_id})')

    # Notification for claimer (if different from owner)
    if item.last_updated_by_id and item.last_updated_by_id != item.user_id and item.status in ['Claimed', 'Purchased']:
        claimer_message = f"💰 Price drop on '{item.description[:50]}' you claimed! Now ${new_price:.2f} (was ${old_price:.2f})"
        create_notification(item.last_updated_by_id, claimer_message, "/my-claims")
        logger.info(f'Created price drop notification for claimer (user_id={item.last_updated_by_id})')

    db.session.commit()


def get_items_needing_update(Item, db, cutoff_date, force_all=False):
    """Query items that need price updates based on schedule or force flag."""
    query = Item.query.filter(
        Item.link.isnot(None),
        Item.link != ''
    )
    
    if not force_all:
        query = query.filter(
            db.or_(
                Item.price_updated_at.is_(None),
                Item.price_updated_at < cutoff_date
            )
        )
        
    # Potential future optimization: order by priority/staleness
    # query = query.order_by(Item.price_updated_at.asc())
    
    return query.all()


def refresh_item_price(item, db):
    """Refresh the price for a single item.

    Args:
        item: Item model instance
        db: SQLAlchemy database instance

    Returns:
        Tuple of (success: bool, new_price: float or None, message: str)
    """
    if not item.link:
        return False, None, 'Item has no link'

    try:
        new_price = fetch_price(item.link)

        if new_price is not None:
            old_price = item.price
            item.price = new_price
            item.price_updated_at = datetime.datetime.now(datetime.timezone.utc)

            # Record history
            from services.price_history import record_price_history
            record_price_history(item.id, new_price, source='manual')
            
            db.session.commit()

            if old_price is None:
                return True, new_price, f'Price found: ${new_price:.2f}'
            elif abs(old_price - new_price) < 0.01:
                return True, new_price, 'Price confirmed (no change)'
            else:
                return True, new_price, f'Price updated from ${old_price:.2f} to ${new_price:.2f}'
        else:
            # Update timestamp even if fetch failed
            item.price_updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.session.commit()
            return False, None, 'Could not fetch price from URL'

    except Exception as e:
        logger.error(f'Error refreshing price for item {item.id}: {str(e)}')
        db.session.rollback()
        return False, None, f'Error: {str(e)}'
