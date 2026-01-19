"""Identity manager for rotating browser identities."""
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from services.amazon_stealth.identities import BrowserIdentity, IDENTITY_PROFILES

logger = logging.getLogger(__name__)

# How many requests before rotating an identity
MIN_REQUESTS_BEFORE_ROTATE = 10
MAX_REQUESTS_BEFORE_ROTATE = 20

# How long to burn an identity after CAPTCHA
BURN_DURATION_HOURS = 24


class IdentityManager:
    """Manages browser identity rotation and burn tracking."""

    def __init__(self, redis_client):
        """Initialize with Redis client for state persistence.

        Args:
            redis_client: Redis client instance (can be None for testing)
        """
        self.redis = redis_client
        self._identities = [
            BrowserIdentity(**profile) for profile in IDENTITY_PROFILES
        ]

    def _redis_key(self, identity_id: str, suffix: str) -> str:
        """Generate Redis key for identity state."""
        return f"amazon:identity:{identity_id}:{suffix}"

    def _get_request_count(self, identity_id: str) -> int:
        """Get current request count for identity."""
        if not self.redis:
            return 0
        key = self._redis_key(identity_id, "requests")
        value = self.redis.get(key)
        return int(value) if value else 0

    def _is_burned(self, identity_id: str) -> bool:
        """Check if identity is currently burned."""
        if not self.redis:
            return False
        key = self._redis_key(identity_id, "burned")
        value = self.redis.get(key)
        if not value:
            return False
        try:
            burn_until = datetime.fromisoformat(value.decode())
            return datetime.now(timezone.utc) < burn_until
        except (ValueError, AttributeError):
            return False

    def get_healthy_identity(self) -> Optional[BrowserIdentity]:
        """Get a healthy identity with lowest usage.

        Returns identity with lowest request count that isn't burned.
        Returns None if all identities are burned.
        """
        # Filter out burned identities
        healthy = [
            identity for identity in self._identities
            if not self._is_burned(identity.id)
        ]

        if not healthy:
            logger.warning("All Amazon identities are burned!")
            return None

        # Sort by request count (ascending) and pick from lowest
        healthy.sort(key=lambda i: self._get_request_count(i.id))

        # Add some randomization among low-usage identities
        low_usage = [i for i in healthy if self._get_request_count(i.id) <= self._get_request_count(healthy[0].id) + 2]

        return random.choice(low_usage)

    def mark_success(self, identity: BrowserIdentity):
        """Mark successful request for identity.

        Increments request count. Resets cookies after rotation threshold.
        """
        if not self.redis:
            return

        key = self._redis_key(identity.id, "requests")
        count = self.redis.incr(key)

        # Set 24h expiry on request counter
        self.redis.expire(key, 86400)

        # Check if we should rotate
        threshold = random.randint(MIN_REQUESTS_BEFORE_ROTATE, MAX_REQUESTS_BEFORE_ROTATE)
        if count >= threshold:
            logger.info(f"Rotating identity {identity.id} after {count} requests")
            self._reset_identity(identity.id)

    def mark_burned(self, identity: BrowserIdentity):
        """Mark identity as burned (triggered CAPTCHA).

        Identity will be unavailable for BURN_DURATION_HOURS.
        """
        burn_until = datetime.now(timezone.utc) + timedelta(hours=BURN_DURATION_HOURS)

        if self.redis:
            key = self._redis_key(identity.id, "burned")
            self.redis.set(key, burn_until.isoformat())
            self.redis.expire(key, BURN_DURATION_HOURS * 3600)

        logger.warning(f"Burned identity {identity.id} until {burn_until}")

    def _reset_identity(self, identity_id: str):
        """Reset identity state for rotation."""
        if not self.redis:
            return

        # Reset request count
        self.redis.delete(self._redis_key(identity_id, "requests"))

        # Clear cookies (will be regenerated on next use)
        self.redis.delete(self._redis_key(identity_id, "cookies"))

        logger.info(f"Reset identity {identity_id}")

    def save_cookies(self, identity_id: str, cookies: list):
        """Save cookies for identity."""
        if not self.redis:
            return
        import json
        key = self._redis_key(identity_id, "cookies")
        self.redis.set(key, json.dumps(cookies))
        self.redis.expire(key, 86400)  # 24h expiry

    def load_cookies(self, identity_id: str) -> list:
        """Load saved cookies for identity."""
        if not self.redis:
            return []
        import json
        key = self._redis_key(identity_id, "cookies")
        value = self.redis.get(key)
        if value:
            try:
                return json.loads(value.decode())
            except (json.JSONDecodeError, AttributeError):
                pass
        return []
