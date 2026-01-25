"""Tests for Amazon stealth identity manager."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

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
        """Should return a healthy identity when available."""
        identity = manager.get_healthy_identity()
        assert identity is not None
        assert isinstance(identity, BrowserIdentity)

    def test_get_healthy_identity_skips_burned(self, manager, mock_redis):
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

    def test_get_healthy_identity_returns_none_when_all_burned(
            self, manager, mock_redis):
        """Should return None when all identities are burned."""
        future = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        mock_redis.get.return_value = future.encode()

        identity = manager.get_healthy_identity()
        assert identity is None

    def test_mark_success_increments_request_count(self, manager, mock_redis):
        """Should increment request count on success."""
        identity = manager.get_healthy_identity()
        manager.mark_success(identity)

        mock_redis.incr.assert_called()

    def test_mark_burned_sets_burn_timestamp(self, manager, mock_redis):
        """Should set burn timestamp when identity is burned."""
        identity = manager.get_healthy_identity()
        manager.mark_burned(identity)

        mock_redis.set.assert_called()
        call_args = mock_redis.set.call_args
        assert ":burned" in call_args[0][0]

    def test_get_healthy_identity_prefers_lowest_request_count(
            self, manager, mock_redis):
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
        # All should be mac_chrome_2 since it's the only one with count <= min
        # + 2
        assert all(i == "mac_chrome_2" for i in ids)
