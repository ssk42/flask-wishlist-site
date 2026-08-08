"""Amazon price extractor."""

import json
import logging
import re

from .base import BasePriceExtractor

logger = logging.getLogger(__name__)


class AmazonPriceExtractor(BasePriceExtractor):
    """Price extractor for Amazon product pages.

    Amazon actively blocks scraping. This extractor tries multiple approaches:
    1. Data attributes (data-asin-price)
    2. CSS selectors for various price display layouts
    3. Embedded JavaScript/JSON data

    For reliable Amazon pricing, consider using the Amazon Product Advertising API.
    """

    domain_patterns = ['amazon.com', 'amazon.co.uk', 'amazon.ca', 'amazon.de',
                       'amazon.fr', 'amazon.es', 'amazon.it', 'amazon.co.jp',
                       'a.co', 'amzn.to', 'amzn.eu']

    # CSS selectors for finding price on Amazon pages (2024-2025 layouts)
    PRICE_SELECTORS = [
        # Main price displays (2024-2025 layouts)
        '#corePrice_feature_div .a-offscreen',
        '#corePriceDisplay_desktop_feature_div .a-offscreen',
        '#apex_offerDisplay_desktop .a-offscreen',
        '.apexPriceToPay .a-offscreen',
        '#tp_price_block_total_price_ww .a-offscreen',
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
        # Try broader selectors last
        '.a-color-price',
        'span[data-a-color="price"] .a-offscreen',
    ]

    # JavaScript patterns for price extraction
    SCRIPT_PATTERNS = [
        r'"priceAmount":\s*([\d.]+)',
        r'"price":\s*"?\$?([\d,.]+)"?',
        r'buyingPrice["\']?\s*:\s*["\']?([\d,.]+)',
    ]

    def extract_from_soup(self, soup):
        """Extract price from Amazon BeautifulSoup object."""
        try:
            # First try: Extract from data-asin-price attribute
            price = self._extract_from_data_attributes(soup)
            if price:
                return price

            # Second try: CSS selectors
            price = self._extract_from_selectors(soup)
            if price:
                return price

            # Third try: Embedded JavaScript data
            price = self._extract_from_scripts(soup)
            if price:
                return price

            return None
        except Exception:
            return None

    def _extract_from_data_attributes(self, soup):
        """Extract price from data-asin-price attribute."""
        price_elem = soup.find(attrs={'data-asin-price': True})
        if price_elem:
            price = self.parse_price(price_elem.get('data-asin-price'))
            if price and price > 0:
                logger.info(f'Found Amazon price from data-asin-price: ${price}')
                return price
        return None

    def _extract_from_selectors(self, soup):
        """Extract price using CSS selectors."""
        for selector in self.PRICE_SELECTORS:
            price_elem = soup.select_one(selector)
            if price_elem:
                price = self.parse_price(price_elem.get_text())
                if price and price > 0:
                    logger.info(f'Found Amazon price: ${price}')
                    return price
        return None

    def _extract_from_scripts(self, soup):
        """Try to extract Amazon price from embedded scripts/data."""
        # Look for price in data attributes
        price_elements = soup.find_all(attrs={'data-asin-price': True})
        for elem in price_elements:
            price = self.parse_price(elem.get('data-asin-price'))
            if price and price > 0:
                return price

        # Look in script tags for price data
        for script in soup.find_all('script'):
            if script.string:
                for pattern in self.SCRIPT_PATTERNS:
                    match = re.search(pattern, script.string)
                    if match:
                        price = self.parse_price(match.group(1))
                        if price and price > 0:
                            logger.info(f'Found Amazon price from script: ${price}')
                            return price
        return None

    def extract_metadata(self, soup):
        """Extract full metadata from Amazon product page."""
        metadata = {
            'title': None,
            'image': None,
            'price': None
        }

        try:
            # Title
            title_elem = soup.select_one('#productTitle') or soup.select_one('#title')
            if title_elem:
                metadata['title'] = title_elem.get_text(strip=True)

            # Price
            metadata['price'] = self.extract_from_soup(soup)

            # Image
            img_elem = soup.select_one('#landingImage') or soup.select_one('#imgBlkFront')
            if img_elem:
                # Try to get high res from data attribute
                if img_elem.get('data-a-dynamic-image'):
                    try:
                        data = json.loads(img_elem['data-a-dynamic-image'])
                        if data:
                            # Get the largest image key
                            metadata['image'] = max(data.keys(), key=lambda k: data[k][0])
                    except (json.JSONDecodeError, KeyError, TypeError):
                        pass
                if not metadata.get('image'):
                    metadata['image'] = img_elem.get('src')

        except Exception as e:
            logger.warning(f'Error extracting Amazon metadata: {e}')

        return metadata
