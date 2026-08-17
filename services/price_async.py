"""Async price fetching service using aiohttp."""
import asyncio
import random
import time
from typing import List, Dict, Optional, Set, Tuple
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
# Retry bot-blocked non-Amazon URLs through the headless browser
BROWSER_RESCUE_ENABLED = Config.BROWSER_RESCUE_ENABLED

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
            logger.warning(f"Could not initialize IdentityManager for async: {e}")
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
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    return aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT))


async def fetch_prices_batch(urls: List[str]) -> Dict[str, Optional[float]]:
    # @spec AUTO-PRC-001
    """Fetch multiple prices concurrently using asyncio.

    # @spec AUTO-PRC-010

    Amazon URLs are routed through the stealth extractor when enabled.
    Amazon stealth requests run SEQUENTIALLY (one at a time) to reduce memory usage.
    Other URLs use standard aiohttp fetching concurrently.
    Bot-blocked (HTTP 403/429) non-Amazon URLs are retried once via the browser.
    """
    results = {}
    blocked_urls: Set[str] = set()

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
            price, status = await _fetch_price_async_standard(url)
            # Browser-rescue candidates:
            #  - explicit bot blocks (403/429), and
            #  - a 200 that yielded no price — the HTML price is often
            #    JS-rendered (e.g. Target) and only a real browser sees it.
            # Network errors (status None) and cache hits are not rescued.
            if price is None and status in (403, 429, 200):
                blocked_urls.add(url)
            return url, price

    try:
        # Handle non-Amazon URLs with standard fetching (concurrent)
        standard_tasks = [fetch_one_standard(url) for url in other_urls]
        
        if standard_tasks:
            completed = await asyncio.gather(*standard_tasks, return_exceptions=True)
            for result in completed:
                if isinstance(result, Exception):
                    logger.error(f"Async batch error: {result}")
                    continue
                if isinstance(result, tuple) and len(result) == 2:
                    url, price = result
                    results[url] = price

        # Browser rescue: bot-blocked (403/429) URLs get one retry through
        # the headless browser — many retailers serve their page to a real
        # browser but 403 plain aiohttp. Runs SEQUENTIALLY (browsers are
        # memory-heavy) and only when stealth infra is available.
        if blocked_urls and BROWSER_RESCUE_ENABLED:
            manager = _get_identity_manager()
            if manager:
                rescued = 0
                logger.info(f"Attempting browser rescue for {len(blocked_urls)} bot-blocked URLs")
                for url in sorted(blocked_urls):
                    identity = manager.get_healthy_identity()
                    if not identity:
                        logger.warning(f"No healthy identity for rescue of {url}")
                        continue
                    # Jitter between browser launches
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                    price = await _fetch_browser_rescue(url, identity, manager)
                    if price is not None:
                        results[url] = price
                        rescued += 1
                logger.info(f"Browser rescue complete: {rescued}/{len(blocked_urls)} URLs rescued")
            else:
                logger.warning("IdentityManager not available, skipping browser rescue")
        
        # Handle Amazon URLs with stealth extraction SEQUENTIALLY (one at a time)
        # This prevents memory exhaustion from multiple Playwright browsers
        if amazon_urls and AMAZON_STEALTH_ENABLED:
            manager = _get_identity_manager()
            if manager:
                logger.info(f"Processing {len(amazon_urls)} Amazon URLs sequentially via stealth extraction")
                for url in amazon_urls:
                    identity = manager.get_healthy_identity()
                    if identity:
                        # Add jitter between requests
                        await asyncio.sleep(random.uniform(1.0, 3.0))
                        price = await _fetch_amazon_stealth(url, identity, manager)
                        results[url] = price
                    else:
                        logger.warning(f"No healthy identity available for {url}")
                        results[url] = None
            else:
                logger.warning("IdentityManager not available, skipping Amazon stealth extraction")
                # Fall back to standard fetching for Amazon URLs (likely to fail)
                for url in amazon_urls:
                    async with semaphore:
                        await asyncio.sleep(random.uniform(0.1, 1.0))
                        price = await _fetch_price_async_standard(url)
                        results[url] = price
        elif amazon_urls:
            # Stealth not enabled, use standard fetching (likely to fail)
            logger.info("Amazon stealth disabled, using standard fetch for Amazon URLs")
            for url in amazon_urls:
                async with semaphore:
                    await asyncio.sleep(random.uniform(0.1, 1.0))
                    price = await _fetch_price_async_standard(url)
                    results[url] = price
        
        return results
                
    except Exception as e:
        logger.error(f"Global async batch failure: {e}")
        
    return results


async def _fetch_amazon_stealth(url: str, identity, manager) -> Optional[float]:
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
        from services.amazon_stealth import stealth_fetch_amazon, AmazonFailureType
        
        result = await stealth_fetch_amazon(url, identity, manager)
        
        if result.success:
            manager.mark_success(identity)
            price = result.price
            success = True
            logger.info(f"Stealth extraction succeeded for {url}: ${price}")
        elif result.failure_type == AmazonFailureType.CAPTCHA:
            manager.mark_burned(identity)
            error_type = "CAPTCHA"
            logger.warning(f"Stealth extraction hit CAPTCHA for {url}, identity burned")
        elif result.failure_type == AmazonFailureType.RATE_LIMITED:
            error_type = "RATE_LIMITED"
            logger.warning(f"Stealth extraction rate limited for {url}")
        else:
            error_type = str(result.failure_type) if result.failure_type else "UNKNOWN"
            logger.warning(f"Stealth extraction failed ({result.failure_type}): {url}")
            
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


async def _fetch_browser_rescue(url: str, identity, manager) -> Optional[float]:
    """Retry a bot-blocked (403/429) URL through the headless browser.

    Up to two attempts per URL: the caller-provided identity, then — on
    failure — a different identity from the manager (some soft blocks are
    fingerprint-sensitive). Each attempt mirrors the Amazon stealth recipe:
    identity fingerprint, stealth patches, human-like behaviour (cookie
    banner, mouse, scroll), a wait for an actual price element, and
    anti-bot-wall detection. Sequential by the caller; one browser at a time.

    Returns the parsed price, or None on failure.
    """
    start_time = time.time()
    success = False
    price = None
    error_type = None

    async def attempt(ident) -> Tuple[Optional[float], str]:
        """One full browser fetch+parse of the URL with the given identity."""
        try:
            from playwright.async_api import async_playwright
            from playwright_stealth import Stealth
            from services.amazon_stealth.behaviors import interact_like_human

            stealth = Stealth(
                webgl_vendor_override=ident.webgl_vendor,
                webgl_renderer_override=ident.webgl_renderer,
            )

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    context = await browser.new_context(
                        user_agent=ident.user_agent,
                        viewport=ident.viewport,
                        locale=ident.locale,
                        timezone_id=ident.timezone,
                        color_scheme=ident.color_scheme,
                        device_scale_factor=ident.device_scale,
                        ignore_https_errors=True,
                    )
                    if manager:
                        cookies = manager.load_cookies(ident.id)
                        if cookies:
                            await context.add_cookies(cookies)

                    page = await context.new_page()
                    await stealth.apply_stealth_async(page)

                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)

                    try:
                        await interact_like_human(page)
                    except Exception:
                        pass

                    body_text = await page.evaluate("document.body ? document.body.innerText : ''")
                    if _looks_robot_blocked(body_text):
                        return None, 'ROBOT_BLOCK'

                    try:
                        await page.wait_for_selector(_PRICE_WAIT_SELECTORS, timeout=8000)
                    except Exception:
                        pass  # no price element; still attempt parse (meta tags may carry it)

                    content = await page.content()
                    price_here = _parse_content(url, content)
                    if price_here is not None and manager:
                        manager.save_cookies(ident.id, await context.cookies())
                    return price_here, None
                finally:
                    await browser.close()
        except Exception as e:
            return None, str(e)

    # Attempt 1: the identity the caller chose.
    price, error_type = await attempt(identity)

    # Attempt 2: a different identity — some soft blocks are fingerprint bound.
    if price is None and manager is not None:
        second = None
        for _ in range(3):
            candidate = manager.get_healthy_identity()
            if candidate is not None and (second is None or candidate.id != identity.id):
                second = candidate
                break
        if second is not None:
            price2, error_type2 = await attempt(second)
            if price2 is not None:
                price = price2
                error_type = None
            else:
                error_type = error_type2 or error_type

    if price is not None:
        success = True

    duration_ms = int((time.time() - start_time) * 1000)
    try:
        price_metrics.log_extraction_attempt(
            url=url,
            success=success,
            price=price,
            method='browser_rescue',
            error_type=error_type,
            response_time_ms=duration_ms
        )
    except Exception as e:
        logger.error(f"Failed to log rescue metric: {e}")
    return price


# DOM selectors that the generic/site extractors look for — if any is present
# (JS-rendered), the price is likely extractable. Comma-joined for Playwright.
_PRICE_WAIT_SELECTORS = ','.join([
    'meta[property="og:price:amount"]', 'meta[property="product:price:amount"]',
    'meta[name="price"]', '[itemprop="price"]',
    '.price', '.product-price', '.current-price', '.sale-price', '.regular-price',
    '.product__price', '[data-price]', '[data-product-price]', '.price-value',
    '.woocommerce-Price-amount', '.shopify-Price',
])

# Strong signals of an anti-bot interstitial rather than a product page.
_ROBOT_BLOCK_MARKERS = (
    'captcha', 'robot check', 'verify you are human', 'unusual traffic',
    'checking your browser', 'access denied', 'blocked by',
)


def _looks_robot_blocked(text: str) -> bool:
    """True if page text looks like an anti-bot wall (Cloudflare/DataDome et al)."""
    low = (text or '').lower()
    return any(marker in low for marker in _ROBOT_BLOCK_MARKERS)


async def _fetch_price_async_standard(url: str) -> Tuple[Optional[float], Optional[int]]:
    """Async version of fetch_price for non-Amazon URLs using aiohttp.

    Returns (price, http_status): status is None for cache hits and network
    errors, and the real HTTP status otherwise — so callers can distinguish
    a bot block (403/429) from a parse failure or network error.
    """
    if not url:
        return None, None

    # Check cache first (sync call is fine for Redis usually, or we could use aioredis in future)
    # Since flask-caching is sync, we just call it. Ideally this shouldn't block loop too much.
    cached_text = price_cache.get_cached_response(url)
    if cached_text:
        return _parse_content(url, cached_text), None

    start_time = time.time()
    success = False
    price = None
    error_type = None

    try:
        async with await _get_async_session() as session:
            async with session.get(url, allow_redirects=True, ssl=False) as response:  # nosec B501
                if response.status != 200:
                    error_type = f"HTTP {response.status}"
                    logger.warning(f"Async fetch failed for {url}: {response.status}")
                    return None, response.status

                text = await response.text()

                price = _parse_content(url, text)
                if price:
                    success = True
                    # Cache only price-bearing responses — a 200 with no price
                    # is often JS-rendered (Target et al.) and must be retried,
                    # not shelved in the cache at empty for the next 7 days.
                    price_cache.cache_response(url, text)

                return price, response.status

    except Exception as e:
        error_type = str(e)
        logger.warning(f"Async fetch exception for {url}: {e}")
        return None, None
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        # We record metrics synchronously (SQLAlchemy is sync)
        # In a high-perf async app, we'd queue this logging or use async DB driver.
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
    price, _status = await _fetch_price_async_standard(url)
    return price


def _parse_content(url: str, html_content: str) -> Optional[float]:
    """Parse price from HTML content using the site-appropriate extractor."""
    try:
        from services.price_extraction.extractors import get_extractor_for_url
        soup = BeautifulSoup(html_content, 'html.parser')
        return get_extractor_for_url(url).extract_from_soup(soup)
    except Exception as e:
        logger.error(f"Parsing failed for {url}: {e}")
        return None
