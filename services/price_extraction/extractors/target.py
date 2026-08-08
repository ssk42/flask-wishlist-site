"""Target price extractor."""

import json
import logging

from .base import BasePriceExtractor

logger = logging.getLogger(__name__)


class TargetPriceExtractor(BasePriceExtractor):
    """Price extractor for Target product pages.

    Target heavily relies on JavaScript and API calls via __NEXT_DATA__.
    This extractor tries:
    1. JSON-LD structured data
    2. CSS selectors for various price display layouts
    """

    domain_patterns = ['target.com']

    # CSS selectors for finding price on Target pages (updated for 2024/2025)
    PRICE_SELECTORS = [
        '[data-test="product-price"]',
        '.styles_CurrentPrice',
        '[data-test="current-price"]',
        '[data-test="product-price-container"] span',
    ]

    def extract_from_soup(self, soup):
        """Extract price from Target BeautifulSoup object."""
        try:
            # Try JSON-LD first (most reliable when available)
            price = self._extract_from_json_ld(soup)
            if price:
                return price

            # Try CSS selectors
            price = self._extract_from_selectors(soup)
            if price:
                return price

            return None
        except Exception:
            return None

    def _extract_from_json_ld(self, soup):
        """Extract price from JSON-LD structured data."""
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                if script.string:
                    data = json.loads(script.string)
                    price = self._find_price_in_json_ld(data)
                    if price:
                        logger.info(f'Found Target price from JSON-LD: ${price}')
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

            # Check @graph for nested data
            if '@graph' in data:
                return self._find_price_in_json_ld(data['@graph'])

            # Recurse into dict values
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

    def _extract_from_selectors(self, soup):
        """Extract price using CSS selectors."""
        for selector in self.PRICE_SELECTORS:
            elem = soup.select_one(selector)
            if elem:
                price = self.parse_price(elem.get_text())
                if price and price > 0:
                    logger.info(f'Found Target price via selector: ${price}')
                    return price
        return None
