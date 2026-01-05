"""Async price fetching service using aiohttp."""
import asyncio
import logging
import random
import time
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from services import price_cache, price_metrics
from services.price_service import USER_AGENTS, logger, _parse_price

# Configuration
MAX_CONCURRENT_REQUESTS = 5
REQUEST_TIMEOUT = 15

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
    """Fetch multiple prices concurrently using asyncio."""
    results = {}
    
    # We'll use a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async def fetch_one(url: str):
        async with semaphore:
            # Jitter to avoid thundering herd and strict rate limit checks
            await asyncio.sleep(random.uniform(0.1, 1.0))
            price = await _fetch_price_async(url)
            return url, price

    try:
        tasks = [fetch_one(url) for url in urls if url]
        if not tasks:
            return {}
            
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed:
            if isinstance(result, Exception):
                logger.error(f"Async batch error: {result}")
                continue
            if isinstance(result, tuple) and len(result) == 2:
                url, price = result
                results[url] = price
                
    except Exception as e:
        logger.error(f"Global async batch failure: {e}")
        
    return results

async def _fetch_price_async(url: str) -> Optional[float]:
    """Async version of fetch_price for a single URL."""
    if not url:
        return None

    # Check cache first (sync call is fine for Redis usually, or we could use aioredis in future)
    # Since flask-caching is sync, we just call it. Ideally this shouldn't block loop too much.
    cached_text = price_cache.get_cached_response(url)
    if cached_text:
        return _parse_content(url, cached_text)

    start_time = time.time()
    success = False
    price = None
    error_type = None

    try:
        async with await _get_async_session() as session:
            async with session.get(url, allow_redirects=True, ssl=False) as response:
                if response.status != 200:
                    error_type = f"HTTP {response.status}"
                    logger.warning(f"Async fetch failed for {url}: {response.status}")
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

def _parse_content(url: str, html_content: str) -> Optional[float]:
    """Parse price from HTML content based on domain.
    
    This function duplicates some logic from price_service.py's parsing steps
    to avoid refactoring the entire legacy service immediately.
    Ideally, price_service.py would expose `parse_amazon(soup)` independent of fetching.
    For now, we implement a lightweight parser or import if possible.
    """
    try:
        from services import price_service
        soup = BeautifulSoup(html_content, 'html.parser')
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if 'amazon' in domain or domain in ['a.co', 'amzn.to', 'amzn.eu']:
             # Use the parsing logic from price_service if available or reimplement reuse
             # Since _extract_amazon_price_from_soup exists in price_service (implied by previous context)
             # we should try to use it if exposed, or verify if it's private.
             # It seems to be private `_extract_amazon_price_from_soup` but we can access it.
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
