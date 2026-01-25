"""Stealth extraction for Amazon prices."""
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from bs4 import BeautifulSoup

from services.amazon_stealth.identities import BrowserIdentity
from services.amazon_stealth.behaviors import interact_like_human

logger = logging.getLogger(__name__)


class AmazonFailureType(Enum):
    """Types of Amazon extraction failures."""
    CAPTCHA = "captcha"
    RATE_LIMITED = "rate_limited"
    NO_PRICE_FOUND = "no_price"
    NETWORK_ERROR = "network"


@dataclass
class ExtractionResult:
    """Result of an extraction attempt."""
    success: bool
    price: Optional[float] = None
    failure_type: Optional[AmazonFailureType] = None
    content: Optional[str] = None


def classify_failure(content: str, status_code: int) -> AmazonFailureType:
    """Classify the type of extraction failure.

    Args:
        content: Page HTML content
        status_code: HTTP status code

    Returns:
        AmazonFailureType enum value
    """
    content_lower = content.lower()

    # Check for CAPTCHA/bot detection
    if 'captcha' in content_lower or 'robot check' in content_lower:
        return AmazonFailureType.CAPTCHA

    # Check for rate limiting
    if status_code in (429, 503):
        return AmazonFailureType.RATE_LIMITED

    # Default to no price found
    return AmazonFailureType.NO_PRICE_FOUND


async def stealth_fetch_amazon(
    url: str,
    identity: BrowserIdentity,
    identity_manager=None
) -> ExtractionResult:
    """Fetch Amazon price using full stealth mode.

    Args:
        url: Amazon product URL
        identity: Browser identity to use
        identity_manager: Optional manager for cookie persistence

    Returns:
        ExtractionResult with price or failure info
    """
    from playwright.async_api import async_playwright

    try:
        from playwright_stealth import Stealth
    except ImportError:
        logger.error("playwright-stealth not installed")
        return ExtractionResult(
            success=False,
            failure_type=AmazonFailureType.NETWORK_ERROR
        )

    stealth = Stealth(
        webgl_vendor_override=identity.webgl_vendor,
        webgl_renderer_override=identity.webgl_renderer,
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        try:
            # Create context with identity fingerprint
            context = await browser.new_context(
                user_agent=identity.user_agent,
                viewport=identity.viewport,
                locale=identity.locale,
                timezone_id=identity.timezone,
                color_scheme=identity.color_scheme,
                device_scale_factor=identity.device_scale,
            )

            # Load saved cookies if available
            if identity_manager:
                cookies = identity_manager.load_cookies(identity.id)
                if cookies:
                    await context.add_cookies(cookies)

            page = await context.new_page()

            # Apply stealth patches
            await stealth.apply_stealth_async(page)

            # Navigate with timeout
            try:
                response = await page.goto(
                    url,
                    timeout=30000,
                    wait_until='domcontentloaded'
                )
                response.status if response else 0
            except Exception as e:
                logger.warning(f"Navigation failed for {url}: {e}")
                return ExtractionResult(
                    success=False,
                    failure_type=AmazonFailureType.NETWORK_ERROR
                )

            # Human-like interaction
            await interact_like_human(page)

            # Get page content
            content = await page.content()

            # Check for CAPTCHA/blocking
            lower_content = content.lower()
            if 'captcha' in lower_content or 'robot check' in lower_content:
                logger.warning(f"CAPTCHA detected for {url}")
                return ExtractionResult(
                    success=False,
                    failure_type=AmazonFailureType.CAPTCHA,
                    content=content
                )

            # Extract price using existing logic
            from services.price_service import _extract_amazon_price_from_soup
            soup = BeautifulSoup(content, 'html.parser')
            price = _extract_amazon_price_from_soup(soup)

            # Save cookies for next time
            if identity_manager:
                cookies = await context.cookies()
                identity_manager.save_cookies(identity.id, cookies)

            if price:
                logger.info(f"Successfully extracted Amazon price: ${price}")
                return ExtractionResult(
                    success=True, price=price, content=content)
            else:
                return ExtractionResult(
                    success=False,
                    failure_type=AmazonFailureType.NO_PRICE_FOUND,
                    content=content
                )

        except Exception as e:
            logger.error(f"Stealth extraction failed: {e}")
            return ExtractionResult(
                success=False,
                failure_type=AmazonFailureType.NETWORK_ERROR
            )

        finally:
            await browser.close()


def stealth_fetch_amazon_sync(
    url: str,
    identity: BrowserIdentity,
    identity_manager=None
) -> ExtractionResult:
    """Synchronous wrapper for stealth_fetch_amazon.

    Args:
        url: Amazon product URL
        identity: Browser identity to use
        identity_manager: Optional manager for cookie persistence

    Returns:
        ExtractionResult with price or failure info
    """
    return asyncio.run(stealth_fetch_amazon(url, identity, identity_manager))
