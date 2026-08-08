"""Price extraction package: pluggable per-site price and metadata extractors.

Parsing lives here; fetching (sessions, retries, caching, Playwright,
Amazon stealth) lives in services.price_service, which delegates to the
extractor registry below.
"""

from services.price_extraction.extractors import (
    BasePriceExtractor,
    AmazonPriceExtractor,
    BestBuyPriceExtractor,
    EtsyPriceExtractor,
    GenericPriceExtractor,
    TargetPriceExtractor,
    WalmartPriceExtractor,
    EXTRACTORS,
    get_extractor_for_url,
)
from services.price_extraction.parser import parse_price, get_domain

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
    'parse_price',
    'get_domain',
]
