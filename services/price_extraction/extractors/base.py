"""Base class for price extractors."""

import logging
from abc import ABC, abstractmethod

from bs4 import BeautifulSoup

from services.price_extraction.parser import parse_price

logger = logging.getLogger(__name__)


class BasePriceExtractor(ABC):
    """Abstract base class for site-specific price extractors.

    Subclasses must implement:
    - domain_patterns: List of domain patterns to match (e.g., ['amazon.com'])
    - extract_from_soup(soup): Extract price from BeautifulSoup object

    Optional overrides:
    - extract_from_response(response): Custom response handling
    - extract_metadata(soup): Extract full metadata (title, image, price)
    """

    # Domain patterns this extractor handles
    domain_patterns = []

    @classmethod
    def matches_url(cls, url):
        """Check if this extractor handles the given URL.

        Args:
            url: URL string to check

        Returns:
            True if this extractor can handle the URL
        """
        if not url:
            return False
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        for pattern in cls.domain_patterns:
            if pattern in domain:
                return True
        return False

    @abstractmethod
    def extract_from_soup(self, soup):
        """Extract price from a BeautifulSoup parsed page.

        Args:
            soup: BeautifulSoup object of the product page

        Returns:
            Float price or None if extraction failed
        """
        pass

    def extract_from_response(self, response):
        """Extract price from an HTTP response.

        Override this method for custom response handling
        (e.g., special headers, cookies, redirects).

        Args:
            response: requests.Response object

        Returns:
            Float price or None if extraction failed
        """
        soup = BeautifulSoup(response.text, 'html.parser')
        return self.extract_from_soup(soup)

    def extract_metadata(self, soup):
        """Extract full metadata from a product page.

        Default implementation returns minimal metadata.
        Override for site-specific metadata extraction.

        Args:
            soup: BeautifulSoup object of the product page

        Returns:
            Dictionary with 'title', 'image', 'price' keys
        """
        price = self.extract_from_soup(soup)
        return {
            'title': self._extract_title(soup),
            'image': self._extract_image(soup),
            'price': price
        }

    def _extract_title(self, soup):
        """Extract product title using common patterns."""
        # Try Open Graph title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()

        # Try regular title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()

        return None

    def _extract_image(self, soup):
        """Extract product image using common patterns."""
        # Try Open Graph image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']

        return None

    @staticmethod
    def parse_price(price_text):
        """Parse price text to float (convenience method)."""
        return parse_price(price_text)
