"""Price fetching service for wishlist items."""
import datetime
import logging
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Default headers to mimic a browser request
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

# Rate limiting: minimum seconds between requests
RATE_LIMIT_SECONDS = 2


def fetch_price(url):
    """Fetch the current price from a product URL.

    Supports:
    - Amazon (amazon.com, amazon.co.uk, etc.)
    - More sites can be added

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

        # Amazon price extraction
        if 'amazon' in domain:
            return _fetch_amazon_price(url)

        # Add more site-specific extractors here as needed
        # For now, try a generic approach for other sites
        return _fetch_generic_price(url)

    except Exception as e:
        logger.warning(f'Failed to fetch price from {url}: {str(e)}')
        return None


def _fetch_amazon_price(url):
    """Fetch price from Amazon product page.

    Args:
        url: Amazon product URL

    Returns:
        Float price or None
    """
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Try various Amazon price selectors
        price_selectors = [
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '#priceblock_saleprice',
            '.a-price .a-offscreen',
            '#corePrice_feature_div .a-offscreen',
            '#apex_offerDisplay_desktop .a-offscreen',
            '.apexPriceToPay .a-offscreen',
            '#tp_price_block_total_price_ww .a-offscreen',
        ]

        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text(strip=True)
                price = _parse_price(price_text)
                if price is not None:
                    logger.info(f'Found Amazon price: ${price} from {url}')
                    return price

        logger.warning(f'Could not find price on Amazon page: {url}')
        return None

    except requests.RequestException as e:
        logger.warning(f'Request failed for Amazon URL {url}: {str(e)}')
        return None


def _fetch_generic_price(url):
    """Try to fetch price from a generic product page.

    This uses common patterns found on e-commerce sites but may not work
    for all sites.

    Args:
        url: Product URL

    Returns:
        Float price or None
    """
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for common price patterns in meta tags
        meta_selectors = [
            ('meta[property="og:price:amount"]', 'content'),
            ('meta[property="product:price:amount"]', 'content'),
            ('meta[name="price"]', 'content'),
        ]

        for selector, attr in meta_selectors:
            element = soup.select_one(selector)
            if element and element.get(attr):
                price = _parse_price(element.get(attr))
                if price is not None:
                    logger.info(f'Found price from meta tag: ${price} from {url}')
                    return price

        # Look for structured data (JSON-LD)
        import json
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                price = _extract_price_from_json_ld(data)
                if price is not None:
                    logger.info(f'Found price from JSON-LD: ${price} from {url}')
                    return price
            except (json.JSONDecodeError, TypeError):
                continue

        # Common price class patterns
        price_classes = [
            '.price',
            '.product-price',
            '.current-price',
            '[data-price]',
            '.sale-price',
        ]

        for selector in price_classes:
            elements = soup.select(selector)
            for element in elements:
                price_text = element.get('data-price') or element.get_text(strip=True)
                price = _parse_price(price_text)
                if price is not None and price > 0:
                    logger.info(f'Found price from class: ${price} from {url}')
                    return price

        logger.warning(f'Could not find price on page: {url}')
        return None

    except requests.RequestException as e:
        logger.warning(f'Request failed for URL {url}: {str(e)}')
        return None


def _extract_price_from_json_ld(data):
    """Extract price from JSON-LD structured data.

    Args:
        data: Parsed JSON-LD data (dict or list)

    Returns:
        Float price or None
    """
    if isinstance(data, list):
        for item in data:
            price = _extract_price_from_json_ld(item)
            if price is not None:
                return price
        return None

    if isinstance(data, dict):
        # Direct price field
        if 'price' in data:
            price = _parse_price(str(data['price']))
            if price is not None:
                return price

        # Offers array
        if 'offers' in data:
            offers = data['offers']
            if isinstance(offers, dict) and 'price' in offers:
                return _parse_price(str(offers['price']))
            if isinstance(offers, list):
                for offer in offers:
                    if isinstance(offer, dict) and 'price' in offer:
                        return _parse_price(str(offer['price']))

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

    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[^\d.,]', '', price_text.strip())

    if not cleaned:
        return None

    # Handle different decimal separators
    # If there's both comma and period, determine which is decimal
    if ',' in cleaned and '.' in cleaned:
        # Usually the last separator is the decimal
        if cleaned.rfind(',') > cleaned.rfind('.'):
            # European format: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # US format: 1,234.56
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        # Could be either 1,234 or 1,50 - check position
        parts = cleaned.split(',')
        if len(parts) == 2 and len(parts[1]) == 2:
            # Likely European decimal
            cleaned = cleaned.replace(',', '.')
        else:
            # Likely thousands separator
            cleaned = cleaned.replace(',', '')

    try:
        return float(cleaned)
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
                    # Even if we couldn't get a price, update the timestamp
                    # to avoid repeatedly trying failed URLs
                    item.price_updated_at = datetime.datetime.now()
                    db.session.commit()
                    logger.info(f'Could not fetch price for item {item.id}, updated timestamp')

                # Rate limiting
                time.sleep(RATE_LIMIT_SECONDS)

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

            if old_price != new_price:
                return True, new_price, f'Price updated from ${old_price:.2f} to ${new_price:.2f}'
            return True, new_price, 'Price confirmed (no change)'
        else:
            # Update timestamp even if fetch failed
            item.price_updated_at = datetime.datetime.now()
            db.session.commit()
            return False, None, 'Could not fetch price from URL'

    except Exception as e:
        logger.error(f'Error refreshing price for item {item.id}: {str(e)}')
        db.session.rollback()
        return False, None, f'Error: {str(e)}'
