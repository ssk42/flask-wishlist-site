"""Generic price extractor for sites without specific extractors."""

import json
import logging

from .base import BasePriceExtractor

logger = logging.getLogger(__name__)


class GenericPriceExtractor(BasePriceExtractor):
    """Fallback price extractor using common patterns.

    Tries multiple strategies in order of reliability:
    1. Meta tags (og:price:amount, product:price:amount)
    2. JSON-LD structured data
    3. Microdata (itemprop="price")
    4. Common CSS class patterns
    """

    domain_patterns = []  # Matches any URL as fallback

    # Meta tag selectors (selector, attribute)
    META_SELECTORS = [
        ('meta[property="og:price:amount"]', 'content'),
        ('meta[property="product:price:amount"]', 'content'),
        ('meta[name="price"]', 'content'),
        ('meta[name="twitter:data1"]', 'content'),
        ('meta[property="og:price"]', 'content'),
    ]

    # Common CSS class patterns for prices
    PRICE_CLASS_SELECTORS = [
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

    @classmethod
    def matches_url(cls, url):
        """Always returns True as this is the fallback extractor."""
        return True

    def extract_from_soup(self, soup):
        """Extract price using multiple strategies."""
        try:
            # Strategy 1: Meta tags (most reliable when available)
            price = self._extract_from_meta_tags(soup)
            if price:
                logger.info(f'Found price from meta tag: ${price}')
                return price

            # Strategy 2: JSON-LD structured data
            price = self._extract_from_json_ld(soup)
            if price:
                logger.info(f'Found price from JSON-LD: ${price}')
                return price

            # Strategy 3: Microdata
            price = self._extract_from_microdata(soup)
            if price:
                logger.info(f'Found price from microdata: ${price}')
                return price

            # Strategy 4: Common CSS class patterns
            price = self._extract_from_css_classes(soup)
            if price:
                return price

            logger.warning('Could not find price on page')
            return None

        except Exception as e:
            logger.warning(f'Generic price extraction failed: {str(e)}')
            return None

    def _extract_from_meta_tags(self, soup):
        """Extract price from meta tags."""
        for selector, attr in self.META_SELECTORS:
            element = soup.select_one(selector)
            if element and element.get(attr):
                price = self.parse_price(element.get(attr))
                if price is not None and price > 0:
                    return price
        return None

    def _extract_from_json_ld(self, soup):
        """Extract price from JSON-LD structured data."""
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                if script.string:
                    data = json.loads(script.string)
                    price = self._find_price_in_json_ld(data)
                    if price:
                        return price
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def _find_price_in_json_ld(self, data):
        """Recursively search for price in JSON-LD data."""
        if isinstance(data, dict):
            # Direct price field
            if 'price' in data:
                price = self.parse_price(data['price'])
                if price:
                    return price

            # Check offers
            if 'offers' in data:
                offers = data['offers']
                if isinstance(offers, dict):
                    if 'price' in offers:
                        return self.parse_price(offers['price'])
                    if 'lowPrice' in offers:
                        return self.parse_price(offers['lowPrice'])
                elif isinstance(offers, list):
                    for offer in offers:
                        if isinstance(offer, dict) and 'price' in offer:
                            return self.parse_price(offer['price'])

            # Recurse
            for value in data.values():
                result = self._find_price_in_json_ld(value)
                if result:
                    return result

        elif isinstance(data, list):
            for item in data:
                result = self._find_price_in_json_ld(item)
                if result:
                    return result

        return None

    def _extract_from_microdata(self, soup):
        """Extract price from microdata attributes."""
        price_elem = soup.find(itemprop='price')
        if price_elem:
            price_val = price_elem.get('content') or price_elem.get_text()
            price = self.parse_price(price_val)
            if price and price > 0:
                return price
        return None

    def _extract_from_css_classes(self, soup):
        """Extract price using common CSS class patterns."""
        for selector in self.PRICE_CLASS_SELECTORS:
            elements = soup.select(selector)
            for element in elements:
                price_text = (
                    element.get('data-price') or
                    element.get('content') or
                    element.get_text(strip=True)
                )
                price = self.parse_price(price_text)
                if price is not None and price > 0 and price < 100000:
                    logger.info(f'Found price from class {selector}: ${price}')
                    return price
        return None
