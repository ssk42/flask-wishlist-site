"""Price fetching service for wishlist items."""
import datetime
import json
import logging
import random
import re
import time
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

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


def _make_request(url, session=None, retries=MAX_RETRIES):
    """Make a request with retry logic."""
    if session is None:
        session = _get_session()

    for attempt in range(retries + 1):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
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
                raise
    return None


def fetch_price(url):
    """Fetch the current price from a product URL.

    Supports:
    - Amazon (amazon.com, amazon.co.uk, etc.)
    - Target (target.com)
    - Walmart (walmart.com)
    - Best Buy (bestbuy.com)
    - Etsy (etsy.com)
    - Generic sites via meta tags and JSON-LD

    Args:
        url: The product URL to fetch the price from

    Returns:
        A float price if found, None if the price cannot be determined
    """
    if not url:
        return None

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Site-specific extractors
        if 'amazon' in domain:
            return _fetch_amazon_price(url)
        elif 'target.com' in domain:
            return _fetch_target_price(url)
        elif 'walmart.com' in domain:
            return _fetch_walmart_price(url)
        elif 'bestbuy.com' in domain:
            return _fetch_bestbuy_price(url)
        elif 'etsy.com' in domain:
            return _fetch_etsy_price(url)

        # Generic approach for other sites
        return _fetch_generic_price(url)

    except Exception as e:
        logger.warning(f'Failed to fetch price from {url}: {str(e)}')
        return None


def _fetch_with_playwright(url):
    """Fetch content using Playwright (headless browser) for stubborn sites."""
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
                soup = BeautifulSoup(content, 'html.parser')
                return soup
            finally:
                browser.close()
                
    except Exception as e:
        logger.error(f"Playwright fetch failed for {url}: {e}")
        return None



def _fetch_amazon_price(url):
    """Fetch price from Amazon product page.

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
            'Host': 'www.amazon.com',
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
            '.reinventPricePriceToPayMargin .a-offscreen',
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
            'span[data-a-color="price"] .a-offscreen',
            '.a-color-price',
        ]

        for selector in price_selectors:
            elements = soup.select(selector)
            for element in elements:
                price_text = element.get_text(strip=True)
                price = _parse_price(price_text)
                if price is not None and price > 0:
                    logger.info(f'Found Amazon price: ${price} using {selector}')
                    return price

        # Third try: Extract from embedded JavaScript data
        price = _extract_amazon_price_from_scripts(soup)
        if price:
            return price
            
        return None  # Let it fall through to the fallback at the end

    except Exception as e:
        logger.warning(f'Amazon price fetch failed for {url}: {str(e)}')
        # Determine if we should try fallback based on error? 
        # For now, let's try fallback if requests fails significantly
        pass
        
    # Final Fallback 
    logger.info(f"Targeting Playwright fallback for {url}")
    soup = _fetch_with_playwright(url)
    if soup:
        # Debug trace
        title = soup.find('title')
        title_text = title.get_text().strip() if title else 'No Title'
        logger.info(f"Playwright loaded Amazon page: {title_text}")
        
        return _extract_amazon_price_from_soup(soup)
        
    return None

def _extract_amazon_price_from_soup(soup):
    """Refactored extraction logic to start with soup."""
    # First try: Extract from twister-plus-price-data-price attribute
    price_elem = soup.find(attrs={'data-asin-price': True})
    if price_elem:
        price = _parse_price(price_elem.get('data-asin-price'))
        if price and price > 0:
            logger.info(f'Found Amazon price via soup data-asin-price: ${price}')
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
        '.reinventPricePriceToPayMargin .a-offscreen',
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
        'span[data-a-color="price"] .a-offscreen',
        '.a-color-price',
    ]

    for selector in price_selectors:
        elements = soup.select(selector)
        for element in elements:
            price_text = element.get_text(strip=True)
            price = _parse_price(price_text)
            if price is not None and price > 0:
                logger.info(f'Found Amazon price via soup: ${price} using {selector}')
                return price

    # Third try: Extract from embedded JavaScript data
    price = _extract_amazon_price_from_scripts(soup)
    if price:
        return price
        
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


def _fetch_target_price(url):
    """Fetch price from Target product page."""
    try:
        # Extract TCIN (Target product ID) from URL
        tcin_match = re.search(r'A-(\d+)', url) or re.search(r'/p/-/A-(\d+)', url)
        if not tcin_match:
            # Try to get TCIN from the page
            response = _make_request(url)
            if not response:
                return None
            tcin_match = re.search(r'"tcin":"(\d+)"', response.text)
            
            # If standard request failed to get TCIN, try Playwright
            if not tcin_match:
                 soup = _fetch_with_playwright(url)
                 if soup:
                     # Try to find TCIN in the full rendered page
                     text = str(soup)
                     tcin_match = re.search(r'"tcin":"(\d+)"', text)
                     
                     # Or try to parse price directly from rendered page 
                     # (reusing the fallback logic below)
                     price = _extract_price_from_target_soup(soup)
                     if price:
                         return price


        if tcin_match:
            tcin = tcin_match.group(1)
            # Use Target's price API
            api_url = f'https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&tcin={tcin}&pricing_store_id=1'

            session = _get_session()
            api_response = session.get(api_url, timeout=REQUEST_TIMEOUT)
            if api_response.ok:
                data = api_response.json()
                price_data = data.get('data', {}).get('product', {}).get('price', {})

                # Try current price first, then regular price
                current_price = price_data.get('current_retail')
                if current_price:
                    logger.info(f'Found Target price: ${current_price}')
                    return float(current_price)

                reg_price = price_data.get('reg_retail')
                if reg_price:
                    logger.info(f'Found Target regular price: ${reg_price}')
                    return float(reg_price)

        # Fallback to page scraping
        response = _make_request(url)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for price in JSON-LD
            price = _extract_price_from_json_ld_all(soup)
            if price:
                return price

            # Try page selectors
            selectors = [
                '[data-test="product-price"]',
                '.styles_CurrentPrice',
                '[data-test="current-price"]',
            ]
            for selector in selectors:
                elem = soup.select_one(selector)
                if elem:
                    price = _parse_price(elem.get_text())
                    if price and price > 0:
                        return price

        # Fallback to Playwright if everything else failed
        logger.info(f"Trying Target fallback via Playwright for {url}")
        soup = _fetch_with_playwright(url)
        if soup:
             price = _extract_price_from_target_soup(soup)
             if price:
                 return price

        return None

    except Exception as e:
        logger.warning(f'Target price fetch failed for {url}: {str(e)}')
        return None

def _extract_price_from_target_soup(soup):
    """Helper to extract Target price from a BeautifulSoup object."""
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


def _fetch_walmart_price(url):
    """Fetch price from Walmart product page."""
    try:
        response = _make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

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
        logger.warning(f'Walmart price fetch failed for {url}: {str(e)}')
        return None


def _fetch_bestbuy_price(url):
    """Fetch price from Best Buy product page."""
    try:
        response = _make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Best Buy price selectors
        selectors = [
            '.priceView-customer-price span',
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

    except Exception as e:
        logger.warning(f'Best Buy price fetch failed for {url}: {str(e)}')
        return None


def _fetch_etsy_price(url):
    """Fetch price from Etsy product page."""
    try:
        response = _make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

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

    except Exception as e:
        logger.warning(f'Etsy price fetch failed for {url}: {str(e)}')
        return None


def _fetch_generic_price(url):
    """Try to fetch price from a generic product page using multiple strategies."""
    try:
        response = _make_request(url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

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

        logger.warning(f'Could not find price on page: {url}')
        return None

    except Exception as e:
        logger.warning(f'Generic price fetch failed for {url}: {str(e)}')
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


def update_stale_prices(app, db, Item):
    """Update prices for items that haven't been updated in 7 days.

    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
        Item: Item model class

    Returns:
        Dictionary with counts of items processed, updated, and errors
    """
    with app.app_context():
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)

        # Find items with links that need updating
        items = Item.query.filter(
            Item.link.isnot(None),
            Item.link != '',
            db.or_(
                Item.price_updated_at.is_(None),
                Item.price_updated_at < seven_days_ago
            )
        ).all()

        stats = {
            'items_processed': 0,
            'prices_updated': 0,
            'errors': 0
        }

        for item in items:
            stats['items_processed'] += 1

            try:
                new_price = fetch_price(item.link)

                if new_price is not None:
                    old_price = item.price
                    item.price = new_price
                    item.price_updated_at = datetime.datetime.now()
                    db.session.commit()

                    if old_price != new_price:
                        logger.info(f'Updated price for item {item.id}: ${old_price} -> ${new_price}')
                    stats['prices_updated'] += 1
                else:
                    # Update timestamp to avoid repeatedly trying failed URLs
                    item.price_updated_at = datetime.datetime.now()
                    db.session.commit()
                    logger.info(f'Could not fetch price for item {item.id}, updated timestamp')

                # Rate limiting between requests
                time.sleep(RATE_LIMIT_SECONDS + random.uniform(0, 1))

            except Exception as e:
                logger.error(f'Error updating price for item {item.id}: {str(e)}')
                stats['errors'] += 1
                db.session.rollback()

        logger.info(f'Price update complete: {stats}')
        return stats


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
