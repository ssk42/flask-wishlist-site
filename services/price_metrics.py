"""Metrics and logging for price crawler."""
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from enum import Enum
from models import db, PriceExtractionLog

logger = logging.getLogger(__name__)


class ExtractionError(Enum):
    CAPTCHA = "captcha"
    BOT_BLOCKED = "bot_blocked"
    TIMEOUT = "timeout"
    NO_PRICE_FOUND = "no_price_found"
    INVALID_PAGE = "invalid_page"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


def log_extraction_attempt(
        url,
        success,
        price=None,
        method=None,
        error_type=None,
        response_time_ms=None):
    """Log an extraction attempt to the database."""
    try:
        # Extract domain from URL
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        # Convert Enum to string if needed
        error_str = None
        if error_type:
            if isinstance(error_type, Enum):
                error_str = error_type.value
            else:
                error_str = str(error_type)[:50]

        log = PriceExtractionLog(
            domain=domain,
            url=url[:2048],  # Truncate to fit column
            success=success,
            price=price,
            extraction_method=method,
            error_type=error_str,
            response_time_ms=response_time_ms
        )
        db.session.add(log)
        db.session.commit()

    except Exception as e:
        logger.error(f"Failed to log extraction attempt: {e}")
        db.session.rollback()


def log_stealth_extraction(
    url: str,
    identity_id: str,
    success: bool,
    failure_type: str = None,
    response_time_ms: int = None
):
    """Log stealth extraction attempt for monitoring.

    Args:
        url: The URL that was fetched
        identity_id: The browser identity used
        success: Whether extraction succeeded
        failure_type: Type of failure (captcha, rate_limited, etc.)
        response_time_ms: Response time in milliseconds
    """
    domain = urlparse(url).netloc.lower() if url else "unknown"
    if domain.startswith('www.'):
        domain = domain[4:]

    log = PriceExtractionLog(
        domain=domain,
        url=url[:2048] if url else None,
        success=success,
        extraction_method=f"stealth:{identity_id}",
        error_type=failure_type,
        response_time_ms=response_time_ms,
        created_at=datetime.now(timezone.utc)
    )

    try:
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to log stealth extraction: {e}")
