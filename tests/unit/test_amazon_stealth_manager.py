"""Tests for Amazon stealth identity manager."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from services.amazon_stealth.identity_manager import IdentityManager
from services.amazon_stealth.identities import BrowserIdentity


class TestIdentityManager:
    """Tests for IdentityManager class."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = MagicMock()
        redis.get.return_value = None
        redis.incr.return_value = 1
        return redis

    @pytest.fixture
    def manager(self, mock_redis):
        """Create an IdentityManager with mock Redis."""
        return IdentityManager(mock_redis)

    def test_get_healthy_identity_returns_identity(self, manager):
        # @spec AUTO-STL-001
        """Should return a healthy identity when available."""
        identity = manager.get_healthy_identity()
        assert identity is not None
        assert isinstance(identity, BrowserIdentity)

    def test_get_healthy_identity_skips_burned(self, manager, mock_redis):
        # @spec AUTO-STL-001
        """Should skip identities that are burned."""
        # Burn all but one identity
        future = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

        def mock_get(key):
            if ":burned" in key and "mac_chrome_1" not in key:
                return future.encode()
            return None

        mock_redis.get.side_effect = mock_get

        identity = manager.get_healthy_identity()
        assert identity is not None
        assert identity.id == "mac_chrome_1"

    def test_get_healthy_identity_returns_none_when_all_burned(self, manager, mock_redis):
        # @spec AUTO-STL-004
        """Should return None when all identities are burned."""
        future = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        mock_redis.get.return_value = future.encode()

        identity = manager.get_healthy_identity()
        assert identity is None

    def test_mark_success_increments_request_count(self, manager, mock_redis):
        # @spec AUTO-STL-002
        """Should increment request count on success."""
        identity = manager.get_healthy_identity()
        manager.mark_success(identity)

        mock_redis.incr.assert_called()

    def test_mark_burned_sets_burn_timestamp(self, manager, mock_redis):
        # @spec AUTO-STL-003
        """Should set burn timestamp when identity is burned."""
        identity = manager.get_healthy_identity()
        manager.mark_burned(identity)

        mock_redis.set.assert_called()
        call_args = mock_redis.set.call_args
        assert ":burned" in call_args[0][0]

    def test_get_healthy_identity_prefers_lowest_request_count(self, manager, mock_redis):
        # @spec AUTO-STL-001
        """Should prefer identities with lowest request count."""
        def mock_get(key):
            if "mac_chrome_1:requests" in key:
                return b"100"
            if "mac_chrome_2:requests" in key:
                return b"50"
            # All other identities have high request counts
            if ":requests" in key:
                return b"99"
            return None

        mock_redis.get.side_effect = mock_get

        # Run multiple times, should prefer mac_chrome_2 (lowest count)
        identities = [manager.get_healthy_identity() for _ in range(5)]
        ids = [i.id for i in identities]
        # mac_chrome_2 has count 50, which is lowest
        # All should be mac_chrome_2 since it's the only one with count <= min + 2
        assert all(i == "mac_chrome_2" for i in ids)

    def test_save_and_load_cookies_roundtrip(self, manager, mock_redis):
        # @spec AUTO-STL-005
        """Cookies persist: save writes JSON to Redis with 24h expiry, load restores."""
        cookies = [{"name": "session-id", "value": "abc", "domain": ".amazon.com"}]
        manager.save_cookies("mac_chrome_1", cookies)

        # save: writes the cookies key and applies a 24h TTL
        assert any("cookies" in str(call[0][0]) for call in mock_redis.set.call_args_list)
        mock_redis.expire.assert_called()

        # load: restore exactly what was saved (JSON round-trip through Redis)
        captured = None
        for call in mock_redis.set.call_args_list:
            if "cookies" in str(call[0][0]):
                captured = call[0][1]
        assert captured is not None
        mock_redis.get.return_value = captured if isinstance(captured, bytes) else str(captured).encode()
        assert manager.load_cookies("mac_chrome_1") == cookies

    def test_load_cookies_returns_empty_when_redis_missing(self, manager, mock_redis):
        # @spec AUTO-STL-005
        mock_redis.get.return_value = None
        assert manager.load_cookies("mac_chrome_1") == []



def test_identity_manager_survives_redis_down():
    """A configured-but-unreachable Redis (lazy client, server down) must not
    break identity selection — the crawler degrades instead of raising."""
    from services.amazon_stealth.identity_manager import IdentityManager

    class DownRedis:
        def get(self, key):
            raise ConnectionError("Error 61 connecting to localhost:6379")
        def set(self, *a, **k):
            raise ConnectionError("down")
        def incr(self, key):
            raise ConnectionError("down")
        def expire(self, *a):
            raise ConnectionError("down")
        def delete(self, *a):
            raise ConnectionError("down")

    mgr = IdentityManager(DownRedis())
    # Selection must return an identity (counts/burns degrade to defaults)...
    ident = mgr.get_healthy_identity()
    assert ident is not None
    # ...and mutations must not raise.
    mgr.mark_success(ident)
    mgr.mark_burned(ident)
    mgr.save_cookies(ident.id, [])
    assert mgr.load_cookies(ident.id) == []


class TestStealthContext:
    """Tests for stealth fetch context configuration."""

    @pytest.mark.asyncio
    async def test_context_applies_fingerprint_and_stealth(self):
        # @spec AUTO-STL-006
        import sys, types
        from unittest.mock import AsyncMock, MagicMock, patch
        from services.amazon_stealth.extractor import stealth_fetch_amazon
        from services.amazon_stealth.identities import BrowserIdentity

        _stealth_kwargs = {}
        fake_stealth = MagicMock()
        fake_stealth.apply_stealth_async = AsyncMock()
        stealth_mod = types.ModuleType("playwright_stealth")
        stealth_mod.Stealth = lambda **kwargs: (_stealth_kwargs.update(kwargs), fake_stealth)[1]
        sys.modules["playwright_stealth"] = stealth_mod

        identity = BrowserIdentity(
            id="mac_chrome_1",
            user_agent="Mozilla/5.0 (Macintosh) Firefox/126.0",
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone="America/New_York",
            color_scheme="light",
            device_scale=2,
            webgl_vendor="Google Inc. (Apple)",
            webgl_renderer="ANGLE Apple M1",
        )

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html>no price</html>")
        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_cookies = AsyncMock()
        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_playwright = AsyncMock()
        mock_playwright.__aenter__.return_value = mock_playwright
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("playwright.async_api.async_playwright", return_value=mock_playwright):
            await stealth_fetch_amazon("https://www.amazon.com/dp/B0TEST", identity, identity_manager=None)

        context_kwargs = mock_browser.new_context.call_args[1]
        assert context_kwargs["user_agent"] == identity.user_agent
        assert context_kwargs["viewport"] == identity.viewport
        assert context_kwargs["locale"] == identity.locale
        assert context_kwargs["timezone_id"] == identity.timezone
        assert context_kwargs["color_scheme"] == identity.color_scheme
        assert context_kwargs["device_scale_factor"] == identity.device_scale
        assert _stealth_kwargs["webgl_vendor_override"] == identity.webgl_vendor
        assert _stealth_kwargs["webgl_renderer_override"] == identity.webgl_renderer
