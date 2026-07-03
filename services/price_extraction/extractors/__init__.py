"""Price extractors for different e-commerce platforms."""

from .base import BasePriceExtractor
from .amazon import AmazonPriceExtractor
from .bestbuy import BestBuyPriceExtractor
from .etsy import EtsyPriceExtractor
from .generic import GenericPriceExtractor
from .target import TargetPriceExtractor
from .walmart import WalmartPriceExtractor

# Registry of all available extractors (order matters - checked in order)
EXTRACTORS = [
    AmazonPriceExtractor,
    BestBuyPriceExtractor,
    EtsyPriceExtractor,
    TargetPriceExtractor,
    WalmartPriceExtractor,
    GenericPriceExtractor,  # Always last as fallback
]


def get_extractor_for_url(url):
    """Get the appropriate extractor for a URL.

    Args:
        url: URL string to extract price from

    Returns:
        Instance of appropriate BasePriceExtractor subclass
    """
    for extractor_class in EXTRACTORS:
        if extractor_class.matches_url(url):
            return extractor_class()
    # Should never reach here due to GenericPriceExtractor
    return GenericPriceExtractor()


__all__ = [
    'BasePriceExtractor',
    'AmazonPriceExtractor',
    'BestBuyPriceExtractor',
    'EtsyPriceExtractor',
    'GenericPriceExtractor',
    'TargetPriceExtractor',
    'WalmartPriceExtractor',
    'EXTRACTORS',
    'get_extractor_for_url',
]
