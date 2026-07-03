"""Etsy price extractor."""

import logging

from .base import BasePriceExtractor

logger = logging.getLogger(__name__)


class EtsyPriceExtractor(BasePriceExtractor):
    """Price extractor for Etsy product pages."""

    domain_patterns = ['etsy.com']

    # CSS selectors for finding price on Etsy pages
    PRICE_SELECTORS = [
        '[data-buy-box-listing-price]',
        '.wt-text-title-03',
        '.wt-mr-xs-1',
        'p[class*="Price"]',
    ]

    def extract_from_soup(self, soup):
        """Extract price from Etsy BeautifulSoup object."""
        try:
            # Try CSS selectors
            for selector in self.PRICE_SELECTORS:
                elem = soup.select_one(selector)
                if elem:
                    # Check for data attribute first
                    price_text = elem.get('data-buy-box-listing-price') or elem.get_text()
                    price = self.parse_price(price_text)
                    if price and price > 0:
                        logger.info(f'Found Etsy price: ${price}')
                        return price

            # Try JSON-LD
            price = self._extract_from_json_ld(soup)
            if price:
                return price

            return None
        except Exception:
            return None

    def _extract_from_json_ld(self, soup):
        """Try to extract price from JSON-LD structured data."""
        import json

        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
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
            # Check for offers with price
            if 'offers' in data:
                offers = data['offers']
                if isinstance(offers, dict):
                    if 'price' in offers:
                        return self.parse_price(offers['price'])
                elif isinstance(offers, list) and offers:
                    if 'price' in offers[0]:
                        return self.parse_price(offers[0]['price'])

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
