"""Price fetching service for wishlist items."""
import datetime
import json
import logging
import random
import re
import time
from urllib.parse import urlparse
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from services import price_cache, price_metrics

logger = logging.getLogger(__name__)

# Feature flag for stealth extraction
AMAZON_STEALTH_ENABLED = True

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

        # Site-specific extractors
        if 'amazon' in domain or domain in ['a.co', 'amzn.to', 'amzn.eu']:
            price = _fetch_amazon_price(url)
        elif 'target.com' in domain:
            price = _fetch_target_price(url)
        elif 'walmart.com' in domain:
            price = _fetch_walmart_price(url)
        elif 'bestbuy.com' in domain:
            price = _fetch_bestbuy_price(url)
        elif 'etsy.com' in domain:
            price = _fetch_etsy_price(url)
        else:
            # Generic approach for other sites
            price = _fetch_generic_price(url)

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
    """Legacy price extraction using requests/Playwright fallback.

    Note: Amazon actively blocks scraping. This function tries multiple approaches
    but may fail due to CAPTCHAs, bot detection, or page structure changes.
    For reliable Amazon pricing, consider using the Amazon Product Advertising API.
    """
    try:
        session = _get_session()
        # Add Amazon-specific headers to look more like a real browser
        session.headers.update({
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.amazon.com/',
            'DNT': '1',
        })

        response = _make_request(url, session)
        if not response:
            logger.warning(f'Amazon request failed (possible bot detection): {url}')
            return None

        # Check if we got a CAPTCHA or robot check page
        if 'captcha' in response.text.lower() or 'robot check' in response.text.lower():
            logger.warning(f'Amazon returned CAPTCHA/robot check page via requests, trying Playwright: {url}')
            soup = _fetch_with_playwright(url)
            if soup:
                 return _extract_amazon_price_from_soup(soup)
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        return _extract_amazon_price_from_soup(soup)
    except Exception as e:
        logger.warning(f'Amazon price fetch failed for {url}: {str(e)}')
        return None

def _extract_amazon_price_from_soup(soup):
    """Extract price from Amazon BeautifulSoup object."""
    try:
        # First try: Extract from twister-plus-price-data-price attribute
        price_elem = soup.find(attrs={'data-asin-price': True})
        if price_elem:
            price = _parse_price(price_elem.get('data-asin-price'))
            if price and price > 0:
                logger.info(f'Found Amazon price from data-asin-price: ${price}')
                return price

        # Second try: Extensive list of Amazon price selectors
        price_selectors = [
            # Main price displays (2024-2025 layouts)
            '#corePrice_feature_div .a-offscreen',
            '#corePriceDisplay_desktop_feature_div .a-offscreen',
            '#apex_offerDisplay_desktop .a-offscreen',
            '.apexPriceToPay .a-offscreen',
            '#tp_price_block_total_price_ww .a-offscreen',
            '.priceToPay .a-offscreen',
            '.priceToPay .a-offscreen',
            '.reinventPricePriceToPayMargin .a-offscreen',
            # Book specific
            '#price', 
            '.header-price',
            # Legacy selectors
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '#priceblock_saleprice',
            '.a-price .a-offscreen',
            '#price_inside_buybox',
            '#newBuyBoxPrice',
            '#kindle-price',
            '#price',
            # Try broader selectors last
            '.a-color-price',
            'span[data-a-color="price"] .a-offscreen',
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price = _parse_price(price_elem.get_text())
                if price and price > 0:
                     logger.info(f'Found Amazon price: ${price}')
                     return price

        # Third try: Extract from embedded JavaScript data
        price = _extract_amazon_price_from_scripts(soup)
        if price:
            return price
            
        return None
    except Exception:
        return None



def _extract_amazon_price_from_scripts(soup):
    """Try to extract Amazon price from embedded scripts/data."""
    # Look for price in data attributes
    price_elements = soup.find_all(attrs={'data-asin-price': True})
    for elem in price_elements:
        price = _parse_price(elem.get('data-asin-price'))
        if price and price > 0:
            return price

    # Look in script tags for price data
    for script in soup.find_all('script'):
        if script.string:
            # Look for common Amazon price patterns in JS
            patterns = [
                r'"priceAmount":\s*([\d.]+)',
                r'"price":\s*"?\$?([\d,.]+)"?',
                r'buyingPrice["\']?\s*:\s*["\']?([\d,.]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, script.string)
                if match:
                    price = _parse_price(match.group(1))
                    if price and price > 0:
                        return price
    return None




def _extract_target_price_from_soup(soup):
    """Helper to extract Target price from a BeautifulSoup object."""
    try:
        # Look for price in JSON-LD
        price = _extract_price_from_json_ld_all(soup)
        if price:
            return price

        # Try page selectors (updated for 2024/2025)
        selectors = [
            '[data-test="product-price"]',
            '.styles_CurrentPrice',
            '[data-test="current-price"]',
            '[data-test="product-price-container"] span',
        ]
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                price = _parse_price(elem.get_text())
                if price and price > 0:
                    logger.info(f'Found Target price via soup: ${price}')
                    return price
        return None
    except Exception:
        return None

def _fetch_target_price(url):
    """Fetch price from Target product page."""
    try:
        # Target heavily relies on JS and API calls via __NEXT_DATA__
        # But we can try requests first for static hydration data
        response = _make_request(url)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for bot block
            if "Access Denied" in soup.title.string if soup.title else "":
                logger.warning(f"Target blocked requests for {url}")
            else:
                 price = _extract_target_price_from_soup(soup)
                 if price: 
                     return price

        # Fallback to Playwright if everything else failed
        logger.info(f"Trying Target fallback via Playwright for {url}")
        soup = _fetch_with_playwright(url)
        if soup:
             return _extract_target_price_from_soup(soup)

        return None

    except Exception as e:
        logger.warning(f'Target price fetch failed for {url}: {str(e)}')
        return None


def _fetch_walmart_price(url):
    """Fetch price from Walmart product page."""
    try:
        response = _make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        return _extract_walmart_price_from_soup(soup)
    except Exception as e:
        logger.warning(f'Walmart price fetch failed for {url}: {str(e)}')
        return None

def _extract_walmart_price_from_soup(soup):
    """Extract price from Walmart BeautifulSoup object."""
    try:
        # Walmart uses various price display methods
        selectors = [
            '[itemprop="price"]',
            '.price-characteristic',
            '[data-automation="buybox-price"]',
            '.prod-PriceHero',
            'span[data-testid="price-wrap"]',
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                # Check for content attribute first
                price_val = elem.get('content') or elem.get_text()
                price = _parse_price(price_val)
                if price and price > 0:
                    logger.info(f'Found Walmart price: ${price}')
                    return price

        # Try JSON-LD
        price = _extract_price_from_json_ld_all(soup)
        if price:
            return price

        # Try script data
        for script in soup.find_all('script', id='__NEXT_DATA__'):
            if script.string:
                try:
                    data = json.loads(script.string)
                    price_info = _deep_search_dict(data, 'priceInfo')
                    if price_info:
                        current = price_info.get('currentPrice', {})
                        if isinstance(current, dict):
                            price = current.get('price') or current.get('priceValue')
                        else:
                            price = current
                        if price:
                            return float(price)
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
        return None
    except Exception as e:
        logger.warning(f'Walmart price extraction failed: {str(e)}')
        return None


def _fetch_bestbuy_price(url):
    """Fetch price from Best Buy product page."""
    try:
        response = _make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        return _extract_bestbuy_price_from_soup(soup)
    except Exception as e:
        logger.warning(f'Best Buy price fetch failed for {url}: {str(e)}')
        return None

def _extract_bestbuy_price_from_soup(soup):
    """Extract price from Best Buy BeautifulSoup object."""
    try:
        # Best Buy price selectors
        selectors = [
            '.priceView-hero-price span',
            '[data-testid="customer-price"] span',
            '.pricing-price__regular-price',
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                price = _parse_price(elem.get_text())
                if price and price > 0:
                    logger.info(f'Found Best Buy price: ${price}')
                    return price

        # Try JSON-LD
        price = _extract_price_from_json_ld_all(soup)
        if price:
            return price

        return None
    except Exception:
        return None


def _fetch_etsy_price(url):
    """Fetch price from Etsy product page."""
    try:
        response = _make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        return _extract_etsy_price_from_soup(soup)
    except Exception as e:
        logger.warning(f'Etsy price fetch failed for {url}: {str(e)}')
        return None

def _extract_etsy_price_from_soup(soup):
    """Extract price from Etsy BeautifulSoup object."""
    try:
        # Etsy price selectors
        selectors = [
            '[data-buy-box-listing-price]',
            '.wt-text-title-03',
            '.wt-mr-xs-1',
            'p[class*="Price"]',
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                price_text = elem.get('data-buy-box-listing-price') or elem.get_text()
                price = _parse_price(price_text)
                if price and price > 0:
                    logger.info(f'Found Etsy price: ${price}')
                    return price

        # Try JSON-LD
        price = _extract_price_from_json_ld_all(soup)
        if price:
            return price

        return None
    except Exception:
        return None


def _fetch_generic_price(url):
    """Try to fetch price from a generic product page using multiple strategies."""
    try:
        response = _make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        return _extract_generic_price_from_soup(soup)
    except Exception as e:
        logger.warning(f'Generic price fetch failed for {url}: {str(e)}')
        return None

def _extract_generic_price_from_soup(soup):
    """Extract price from generic page using standard strategies."""
    try:
        # Strategy 1: Meta tags (most reliable when available)
        meta_selectors = [
            ('meta[property="og:price:amount"]', 'content'),
            ('meta[property="product:price:amount"]', 'content'),
            ('meta[name="price"]', 'content'),
            ('meta[name="twitter:data1"]', 'content'),
            ('meta[property="og:price"]', 'content'),
        ]

        for selector, attr in meta_selectors:
            element = soup.select_one(selector)
            if element and element.get(attr):
                price = _parse_price(element.get(attr))
                if price is not None and price > 0:
                    logger.info(f'Found price from meta tag: ${price}')
                    return price

        # Strategy 2: JSON-LD structured data
        price = _extract_price_from_json_ld_all(soup)
        if price:
            logger.info(f'Found price from JSON-LD: ${price}')
            return price

        # Strategy 3: Microdata
        price_elem = soup.find(itemprop='price')
        if price_elem:
            price_val = price_elem.get('content') or price_elem.get_text()
            price = _parse_price(price_val)
            if price and price > 0:
                logger.info(f'Found price from microdata: ${price}')
                return price
        

        # Strategy 4: Common CSS class patterns
        price_classes = [
            '.product-price',
            '.price',
            '.current-price',
            '.sale-price',
            '.regular-price',
            '.product__price',
            '[data-price]',
            '[data-product-price]',
            '.price-value',
            '.price__current',
            '.ProductPrice',
            '.product-single__price',
            '#product-price',
            '.woocommerce-Price-amount',
            '.shopify-Price',
        ]

        for selector in price_classes:
            elements = soup.select(selector)
            for element in elements:
                price_text = element.get('data-price') or element.get('content') or element.get_text(strip=True)
                price = _parse_price(price_text)
                if price is not None and price > 0 and price < 100000:  # Sanity check
                    logger.info(f'Found price from class {selector}: ${price}')
                    return price

        logger.warning('Could not find price on page')
        return None

    except Exception as e:
        logger.warning(f'Generic price extraction failed: {str(e)}')
        return None


def _extract_price_from_json_ld_all(soup):
    """Extract price from all JSON-LD blocks on the page."""
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            if script.string:
                data = json.loads(script.string)
                price = _extract_price_from_json_ld(data)
                if price is not None:
                    return price
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def _extract_price_from_json_ld(data):
    """Extract price from JSON-LD structured data."""
    if isinstance(data, list):
        for item in data:
            price = _extract_price_from_json_ld(item)
            if price is not None:
                return price
        return None

    if isinstance(data, dict):
        # Check @type for Product
        obj_type = data.get('@type', '')
        if isinstance(obj_type, list):
            obj_type = obj_type[0] if obj_type else ''

        # Direct price field
        if 'price' in data:
            price = _parse_price(str(data['price']))
            if price is not None and price > 0:
                return price

        # Offers - can be dict or list
        offers = data.get('offers')
        if offers:
            if isinstance(offers, dict):
                price = offers.get('price')
                if price:
                    parsed = _parse_price(str(price))
                    if parsed and parsed > 0:
                        return parsed
                # Try lowPrice for ranges
                low_price = offers.get('lowPrice')
                if low_price:
                    parsed = _parse_price(str(low_price))
                    if parsed and parsed > 0:
                        return parsed

            elif isinstance(offers, list):
                for offer in offers:
                    if isinstance(offer, dict):
                        price = offer.get('price')
                        if price:
                            parsed = _parse_price(str(price))
                            if parsed and parsed > 0:
                                return parsed

        # Nested product data
        if '@graph' in data:
            return _extract_price_from_json_ld(data['@graph'])

    return None


def _deep_search_dict(data, key):
    """Recursively search for a key in nested dict/list structures."""
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for v in data.values():
            result = _deep_search_dict(v, key)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = _deep_search_dict(item, key)
            if result is not None:
                return result
    return None


def _parse_price(price_text):
    """Parse a price string into a float.

    Args:
        price_text: String like "$19.99", "USD 19.99", "19,99", etc.

    Returns:
        Float price or None if parsing fails
    """
    if not price_text:
        return None

    if isinstance(price_text, (int, float)):
        return float(price_text)

    price_text = str(price_text).strip()

    # Handle price ranges - take the first/lower price
    if ' - ' in price_text or ' to ' in price_text.lower():
        price_text = re.split(r'\s*[-–]\s*|\s+to\s+', price_text, flags=re.IGNORECASE)[0]

    # Remove currency symbols, letters, and extra whitespace
    cleaned = re.sub(r'[^\d.,\s]', '', price_text).strip()

    # Handle multiple prices (take first one)
    if '  ' in cleaned:
        cleaned = cleaned.split()[0]

    if not cleaned:
        return None

    # Handle different decimal separators
    if ',' in cleaned and '.' in cleaned:
        # Determine which is the decimal separator
        if cleaned.rfind(',') > cleaned.rfind('.'):
            # European format: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # US format: 1,234.56
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        parts = cleaned.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Likely European decimal: 19,99
            cleaned = cleaned.replace(',', '.')
        else:
            # Likely thousands separator: 1,234
            cleaned = cleaned.replace(',', '')

    try:
        result = float(cleaned)
        # Sanity check - prices shouldn't be negative or absurdly high
        if result < 0 or result > 1000000:
            return None
        return result
    except ValueError:
        return None



def _fetch_amazon_metadata(url):
    """Fetch all metadata from Amazon."""
    metadata = {}
    
    # Try requests first
    try:
        session = _get_session()
        # Add Amazon-specific headers
        session.headers.update({
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.amazon.com/',
            'DNT': '1',
        })
        response = _make_request(url, session)
        
        soup = None
        if response and 'captcha' not in response.text.lower() and 'robot check' not in response.text.lower():
             soup = BeautifulSoup(response.text, 'html.parser')
        else:
            logger.warning(f'Amazon CAPTCHA detected, switching to Playwright for metadata: {url}')
            soup = _fetch_with_playwright(url)
            
        if soup:
            # Title
            title_elem = soup.select_one('#productTitle') or soup.select_one('#title')
            if title_elem:
                metadata['title'] = title_elem.get_text(strip=True)
                
            # Price
            price = _extract_amazon_price_from_soup(soup)
            if price:
                metadata['price'] = price
                
            # Image
            img_elem = soup.select_one('#landingImage') or soup.select_one('#imgBlkFront')
            if img_elem:
                # Try to get high res from data attribute
                if img_elem.get('data-a-dynamic-image'):
                    try:
                        data = json.loads(img_elem['data-a-dynamic-image'])
                        if data:
                            # Get the largest image key
                            metadata['image_url'] = max(data.keys(), key=lambda k: data[k][0])
                    except:
                        pass
                if not metadata.get('image_url'):
                    metadata['image_url'] = img_elem.get('src')

            return metadata

    except Exception as e:
        logger.warning(f"Error fetching Amazon metadata: {e}")
    
    return metadata


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
                    price = _parse_price(val)
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
            # Microdata
            price_elem = soup.find(itemprop='price')
            if price_elem:
                val = price_elem.get('content') or price_elem.get_text()
                price = _parse_price(val)
                if price: metadata['price'] = price

            # CSS Classes
            if not metadata.get('price'):
                price_classes = [
                    '.product-price', '.price', '.current-price', '.sale-price', 
                    '.product__price', '[data-price]', '.price-value', '.ProductPrice'
                ]
                for selector in price_classes:
                    elements = soup.select(selector)
                    for element in elements:
                        val = element.get('data-price') or element.get('content') or element.get_text(strip=True)
                        price = _parse_price(val)
                        if price and price > 0:
                            metadata['price'] = price
                            break
                    if metadata.get('price'): break

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
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)

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
    # Notification for owner
    owner_message = f"🎉 Price drop! '{item.description[:50]}' is now ${new_price:.2f} (was ${old_price:.2f}) - {drop_percent:.0f}% off!"
    owner_notif = Notification(
        message=owner_message,
        link=f"/items?user_filter={item.user_id}",
        user_id=item.user_id
    )
    db.session.add(owner_notif)
    logger.info(f'Created price drop notification for owner (user_id={item.user_id})')
    
    # Notification for claimer (if different from owner)
    if item.last_updated_by_id and item.last_updated_by_id != item.user_id and item.status in ['Claimed', 'Purchased']:
        claimer_message = f"💰 Price drop on '{item.description[:50]}' you claimed! Now ${new_price:.2f} (was ${old_price:.2f})"
        claimer_notif = Notification(
            message=claimer_message,
            link="/my-claims",
            user_id=item.last_updated_by_id
        )
        db.session.add(claimer_notif)
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
            item.price_updated_at = datetime.datetime.now()
            
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
            item.price_updated_at = datetime.datetime.now()
            db.session.commit()
            return False, None, 'Could not fetch price from URL'

    except Exception as e:
        logger.error(f'Error refreshing price for item {item.id}: {str(e)}')
        db.session.rollback()
        return False, None, f'Error: {str(e)}'
