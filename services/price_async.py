"""Async price fetching service using aiohttp."""
import asyncio
import random
import time
from typing import List, Dict, Optional
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from config import Config
from services import price_cache, price_metrics
from services.price_service import USER_AGENTS, logger

# Configuration
MAX_CONCURRENT_REQUESTS = 5
REQUEST_TIMEOUT = 15

# Amazon stealth feature flag
AMAZON_STEALTH_ENABLED = Config.AMAZON_STEALTH_ENABLED

# Singleton identity manager (lazy initialized)
_identity_manager = None


def _get_identity_manager():
    """Get or create the identity manager singleton for async usage."""
    global _identity_manager
    if _identity_manager is None:
        try:
            from extensions import redis_client
            from services.amazon_stealth import IdentityManager
            _identity_manager = IdentityManager(redis_client)
        except Exception as e:
            logger.warning(
                f"Could not initialize IdentityManager for async: {e}")
            return None
    return _identity_manager


def _is_amazon_url(url: str) -> bool:
    """Check if URL is an Amazon URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    return 'amazon' in domain or domain in ['a.co', 'amzn.to', 'amzn.eu']


async def _get_async_session():
    """Create an aiohttp ClientSession with random user agent."""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': (
            'text/html,application/xhtml+xml,application/xml;q=0.9,'
            'image/avif,image/webp,image/apng,*/*;q=0.8'
        ),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    return aiohttp.ClientSession(
        headers=headers,
        timeout=aiohttp.ClientTimeout(
            total=REQUEST_TIMEOUT))


async def fetch_prices_batch(urls: List[str]) -> Dict[str, Optional[float]]:
    """Fetch multiple prices concurrently using asyncio.

    Amazon URLs are routed through the stealth extractor when enabled.
    Amazon stealth requests run SEQUENTIALLY to reduce memory usage.
    Other URLs use standard aiohttp fetching concurrently.
    """
    results = {}

    # Separate Amazon URLs from others for different handling
    amazon_urls = [url for url in urls if url and _is_amazon_url(url)]
    other_urls = [url for url in urls if url and not _is_amazon_url(url)]

    # We'll use a semaphore to limit concurrency for standard requests
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def fetch_one_standard(url: str):
        """Fetch non-Amazon URL using standard aiohttp."""
        async with semaphore:
            # Jitter to avoid thundering herd and strict rate limit checks
            await asyncio.sleep(random.uniform(0.1, 1.0))
            price = await _fetch_price_async_standard(url)
            return url, price

    try:
        # Handle non-Amazon URLs with standard fetching (concurrent)
        standard_tasks = [fetch_one_standard(url) for url in other_urls]

        if standard_tasks:
            completed = await asyncio.gather(
                *standard_tasks, return_exceptions=True)
            for result in completed:
                if isinstance(result, Exception):
                    logger.error(f"Async batch error: {result}")
                    continue
                if isinstance(result, tuple) and len(result) == 2:
                    url, price = result
                    results[url] = price

        # Handle Amazon URLs with stealth extraction SEQUENTIALLY
        # This prevents memory exhaustion from multiple Playwright browsers
        if amazon_urls and AMAZON_STEALTH_ENABLED:
            manager = _get_identity_manager()
            if manager:
                logger.info(
                    f"Processing {len(amazon_urls)} Amazon URLs "
                    "sequentially via stealth extraction")
                for url in amazon_urls:
                    identity = manager.get_healthy_identity()
                    if identity:
                        # Add jitter between requests
                        await asyncio.sleep(random.uniform(1.0, 3.0))
                        price = await _fetch_amazon_stealth(
                            url, identity, manager)
                        results[url] = price
                    else:
                        logger.warning(
                            f"No healthy identity available for {url}")
                        results[url] = None
            else:
                logger.warning(
                    "IdentityManager not available, "
                    "skipping Amazon stealth extraction")
                # Fall back to standard fetching for Amazon URLs (likely to
                # fail)
                for url in amazon_urls:
                    async with semaphore:
                        await asyncio.sleep(random.uniform(0.1, 1.0))
                        price = await _fetch_price_async_standard(url)
                        results[url] = price
        elif amazon_urls:
            # Stealth not enabled, use standard fetching (likely to fail)
            logger.info(
                "Amazon stealth disabled, using standard fetch "
                "for Amazon URLs")
            for url in amazon_urls:
                async with semaphore:
                    await asyncio.sleep(random.uniform(0.1, 1.0))
                    price = await _fetch_price_async_standard(url)
                    results[url] = price

        return results

    except Exception as e:
        logger.error(f"Global async batch failure: {e}")

    return results


async def _fetch_amazon_stealth(
        url: str,
        identity,
        manager) -> Optional[float]:
    """Fetch Amazon price using stealth extraction.

    Args:
        url: Amazon product URL
        identity: BrowserIdentity to use
        manager: IdentityManager for tracking success/failure

    Returns:
        Price as float, or None if extraction failed
    """
    start_time = time.time()
    success = False
    price = None
    error_type = None

    try:
        from services.amazon_stealth import (
            stealth_fetch_amazon, AmazonFailureType
        )

        result = await stealth_fetch_amazon(url, identity, manager)

        if result.success:
            manager.mark_success(identity)
            price = result.price
            success = True
            logger.info(f"Stealth extraction succeeded for {url}: ${price}")
        elif result.failure_type == AmazonFailureType.CAPTCHA:
            manager.mark_burned(identity)
            error_type = "CAPTCHA"
            logger.warning(
                f"Stealth extraction hit CAPTCHA for {url}, identity burned")
        elif result.failure_type == AmazonFailureType.RATE_LIMITED:
            error_type = "RATE_LIMITED"
            logger.warning(f"Stealth extraction rate limited for {url}")
        else:
            error_type = str(
                result.failure_type) if result.failure_type else "UNKNOWN"
            logger.warning(
                f"Stealth extraction failed ({result.failure_type}): {url}")

        return price

    except Exception as e:
        error_type = str(e)
        logger.error(f"Stealth extraction error for {url}: {e}")
        return None
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        try:
            price_metrics.log_extraction_attempt(
                url=url,
                success=success,
                price=price,
                method='async_stealth',
                error_type=error_type,
                response_time_ms=duration_ms
            )
        except Exception as e:
            logger.error(f"Failed to log stealth metric: {e}")


async def _fetch_price_async_standard(url: str) -> Optional[float]:
    """Async version of fetch_price for non-Amazon URLs using aiohttp."""
    if not url:
        return None

    # Check cache first (sync call is fine for Redis usually)
    # Since flask-caching is sync, we just call it. Ideally this shouldn't
    # block loop too much.
    cached_text = price_cache.get_cached_response(url)
    if cached_text:
        return _parse_content(url, cached_text)

    start_time = time.time()
    success = False
    price = None
    error_type = None

    try:
        async with await _get_async_session() as session:
            # nosec B501
            async with session.get(
                    url, allow_redirects=True, ssl=False) as response:
                if response.status != 200:
                    error_type = f"HTTP {response.status}"
                    logger.warning(
                        f"Async fetch failed for {url}: {response.status}")
                    return None

                text = await response.text()

                # Cache successful response
                if text:
                    price_cache.cache_response(url, text)

                price = _parse_content(url, text)
                if price:
                    success = True

                return price

    except Exception as e:
        error_type = str(e)
        logger.warning(f"Async fetch exception for {url}: {e}")
        return None
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        # We record metrics synchronously (SQLAlchemy is sync)
        # In a high-perf async app, we'd queue this logging or use async DB
        # driver.
        try:
            price_metrics.log_extraction_attempt(
                url=url,
                success=success,
                price=price,
                method='async_aiohttp',
                error_type=error_type,
                response_time_ms=duration_ms
            )
        except Exception as e:
            logger.error(f"Failed to log async metric: {e}")


# Keep the old function name for backwards compatibility
async def _fetch_price_async(url: str) -> Optional[float]:
    """Async version of fetch_price for a single URL.

    Routes Amazon URLs through stealth extraction when enabled.
    """
    if not url:
        return None

    # Route Amazon URLs through stealth if enabled
    if _is_amazon_url(url) and AMAZON_STEALTH_ENABLED:
        manager = _get_identity_manager()
        if manager:
            identity = manager.get_healthy_identity()
            if identity:
                return await _fetch_amazon_stealth(url, identity, manager)
            else:
                logger.warning(f"No healthy identity for {url}, skipping")
                return None

    # Standard fetch for non-Amazon URLs
    return await _fetch_price_async_standard(url)


def _parse_content(url: str, html_content: str) -> Optional[float]:
    """Parse price from HTML content based on domain.

    This function duplicates some logic from price_service.py's parsing steps
    to avoid refactoring the entire legacy service immediately.
    Ideally, price_service.py would expose parse_amazon(soup) separately.
    For now, we implement a lightweight parser or import if possible.
    """
    try:
        from services import price_service
        soup = BeautifulSoup(html_content, 'html.parser')

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if 'amazon' in domain or domain in ['a.co', 'amzn.to', 'amzn.eu']:
            # Use parsing logic from price_service if available
            # _extract_amazon_price_from_soup exists in price_service
            # we should try to use it if exposed, or verify if it's private.
            # It seems to be private `_extract_amazon_price_from_soup` but we
            # can access it.
            if hasattr(price_service, '_extract_amazon_price_from_soup'):
                return price_service._extract_amazon_price_from_soup(soup)

        elif 'target.com' in domain:
            if hasattr(price_service, '_extract_target_price_from_soup'):
                return price_service._extract_target_price_from_soup(soup)

        elif 'walmart.com' in domain:
            if hasattr(price_service, '_extract_walmart_price_from_soup'):
                return price_service._extract_walmart_price_from_soup(soup)

        elif 'bestbuy.com' in domain:
            if hasattr(price_service, '_extract_bestbuy_price_from_soup'):
                return price_service._extract_bestbuy_price_from_soup(soup)

        elif 'etsy.com' in domain:
            if hasattr(price_service, '_extract_etsy_price_from_soup'):
                return price_service._extract_etsy_price_from_soup(soup)

        # Fallback to generic
        if hasattr(price_service, '_extract_generic_price_from_soup'):
            return price_service._extract_generic_price_from_soup(soup)

        return None

    except Exception as e:
        logger.error(f"Parsing failed for {url}: {e}")
        return None
