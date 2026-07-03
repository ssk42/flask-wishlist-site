"""Main fetching functions for price extraction.

This module provides the high-level API for fetching prices and metadata
from product URLs. It delegates to site-specific extractors as needed.
"""

import logging
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .extractors import get_extractor_for_url
from .parser import get_domain

logger = logging.getLogger(__name__)


def fetch_price_modular(url, response_fetcher):
    """Fetch price from a URL using the modular extractor system.

    This function provides the new modular approach to price extraction.
    It's meant to be called from the main price_service with a response fetcher.

    Args:
        url: Product URL to extract price from
        response_fetcher: Callable that takes URL and returns response object

    Returns:
        Float price or None if extraction failed
    """
    if not url:
        return None

    try:
        # Get appropriate extractor for this URL
        extractor = get_extractor_for_url(url)
        extractor_name = extractor.__class__.__name__

        logger.debug(f'Using {extractor_name} for {get_domain(url)}')

        # Fetch the page
        response = response_fetcher(url)
        if not response:
            logger.warning(f'No response from {url}')
            return None

        # Extract price using the extractor
        price = extractor.extract_from_response(response)

        if price:
            logger.info(f'{extractor_name} extracted price ${price} from {get_domain(url)}')
        else:
            logger.warning(f'{extractor_name} failed to extract price from {get_domain(url)}')

        return price

    except Exception as e:
        logger.error(f'Error in modular fetch for {url}: {str(e)}')
        return None


def fetch_metadata_modular(url, response_fetcher):
    """Fetch product metadata from a URL using the modular extractor system.

    Args:
        url: Product URL to extract metadata from
        response_fetcher: Callable that takes URL and returns response object

    Returns:
        Dictionary with 'title', 'image', 'price' keys
    """
    if not url:
        return {'title': None, 'image': None, 'price': None}

    try:
        extractor = get_extractor_for_url(url)
        response = response_fetcher(url)

        if not response:
            return {'title': None, 'image': None, 'price': None}

        soup = BeautifulSoup(response.text, 'html.parser')
        return extractor.extract_metadata(soup)

    except Exception as e:
        logger.error(f'Error fetching metadata for {url}: {str(e)}')
        return {'title': None, 'image': None, 'price': None}
