"""Best Buy price extractor."""

import json
import logging

from .base import BasePriceExtractor

logger = logging.getLogger(__name__)


class BestBuyPriceExtractor(BasePriceExtractor):
    """Price extractor for Best Buy product pages.

    Best Buy uses relatively standard price display patterns:
    1. CSS selectors for price display elements
    2. JSON-LD structured data
    """

    domain_patterns = ['bestbuy.com', 'bestbuy.ca']

    # CSS selectors for finding price on Best Buy pages
    PRICE_SELECTORS = [
        '.priceView-hero-price span',
        '[data-testid="customer-price"] span',
        '.pricing-price__regular-price',
    ]

    def extract_from_soup(self, soup):
        """Extract price from Best Buy BeautifulSoup object."""
        try:
            # Try CSS selectors first
            price = self._extract_from_selectors(soup)
            if price:
                return price

            # Try JSON-LD
            price = self._extract_from_json_ld(soup)
            if price:
                return price

            return None
        except Exception:
            return None

    def _extract_from_selectors(self, soup):
        """Extract price using CSS selectors."""
        for selector in self.PRICE_SELECTORS:
            elem = soup.select_one(selector)
            if elem:
                price = self.parse_price(elem.get_text())
                if price and price > 0:
                    logger.info(f'Found Best Buy price: ${price}')
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
                        logger.info(f'Found Best Buy price from JSON-LD: ${price}')
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
