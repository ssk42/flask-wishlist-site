"""Walmart price extractor."""

import json
import logging

from .base import BasePriceExtractor

logger = logging.getLogger(__name__)


class WalmartPriceExtractor(BasePriceExtractor):
    """Price extractor for Walmart product pages.

    Walmart uses various price display methods including:
    - Microdata (itemprop="price")
    - Data attributes
    - JSON-LD structured data
    - __NEXT_DATA__ script tags with React hydration data
    """

    domain_patterns = ['walmart.com']

    # CSS selectors for finding price on Walmart pages
    PRICE_SELECTORS = [
        '[itemprop="price"]',
        '.price-characteristic',
        '[data-automation="buybox-price"]',
        '.prod-PriceHero',
        'span[data-testid="price-wrap"]',
    ]

    def extract_from_soup(self, soup):
        """Extract price from Walmart BeautifulSoup object."""
        try:
            # Try CSS selectors first
            price = self._extract_from_selectors(soup)
            if price:
                return price

            # Try JSON-LD
            price = self._extract_from_json_ld(soup)
            if price:
                return price

            # Try __NEXT_DATA__ script
            price = self._extract_from_next_data(soup)
            if price:
                return price

            return None
        except Exception as e:
            logger.warning(f'Walmart price extraction failed: {str(e)}')
            return None

    def _extract_from_selectors(self, soup):
        """Extract price using CSS selectors."""
        for selector in self.PRICE_SELECTORS:
            elem = soup.select_one(selector)
            if elem:
                # Check for content attribute first (microdata)
                price_val = elem.get('content') or elem.get_text()
                price = self.parse_price(price_val)
                if price and price > 0:
                    logger.info(f'Found Walmart price: ${price}')
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
                        logger.info(f'Found Walmart price from JSON-LD: ${price}')
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

    def _extract_from_next_data(self, soup):
        """Extract price from __NEXT_DATA__ React hydration data."""
        for script in soup.find_all('script', id='__NEXT_DATA__'):
            if script.string:
                try:
                    data = json.loads(script.string)
                    price_info = self._deep_search_dict(data, 'priceInfo')
                    if price_info:
                        current = price_info.get('currentPrice', {})
                        if isinstance(current, dict):
                            price = current.get('price') or current.get('priceValue')
                        else:
                            price = current
                        if price:
                            logger.info(f'Found Walmart price from __NEXT_DATA__: ${price}')
                            return float(price)
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
        return None

    def _deep_search_dict(self, data, key):
        """Recursively search for a key in nested dict/list structures."""
        if isinstance(data, dict):
            if key in data:
                return data[key]
            for v in data.values():
                result = self._deep_search_dict(v, key)
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._deep_search_dict(item, key)
                if result is not None:
                    return result
        return None
