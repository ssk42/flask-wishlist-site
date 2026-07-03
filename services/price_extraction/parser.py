"""Price parsing utilities for extracting numeric values from price strings."""

import re
from urllib.parse import urlparse


def parse_price(price_text):
    """Parse a price string into a float.

    Handles various formats:
    - Currency symbols: "$19.99", "£19.99", "€19.99"
    - Currency codes: "USD 19.99", "EUR 19,99"
    - European decimals: "19,99"
    - Thousands separators: "1,234.56" or "1.234,56"
    - Price ranges: "$10 - $20" (returns first price)

    Args:
        price_text: String containing a price

    Returns:
        Float price or None if parsing fails
    """
    if not price_text:
        return None

    if isinstance(price_text, (int, float)):
        return float(price_text)

    price_text = str(price_text).strip()

    # Negative values are not valid prices (e.g. "-$10.00")
    if price_text.startswith('-'):
        return None

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


def get_domain(url):
    """Extract the domain from a URL.

    Args:
        url: Full URL string

    Returns:
        Domain without 'www.' prefix, e.g., 'amazon.com'
    """
    if not url:
        return None
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


def is_amazon_url(url):
    """Check if URL is an Amazon product page."""
    domain = get_domain(url)
    return bool(domain and ('amazon.com' in domain or 'amazon.' in domain))


def is_walmart_url(url):
    """Check if URL is a Walmart product page."""
    domain = get_domain(url)
    return bool(domain and 'walmart.com' in domain)


def is_target_url(url):
    """Check if URL is a Target product page."""
    domain = get_domain(url)
    return bool(domain and 'target.com' in domain)


def is_bestbuy_url(url):
    """Check if URL is a Best Buy product page."""
    domain = get_domain(url)
    return bool(domain and 'bestbuy.com' in domain)


def is_etsy_url(url):
    """Check if URL is an Etsy product page."""
    domain = get_domain(url)
    return bool(domain and 'etsy.com' in domain)
