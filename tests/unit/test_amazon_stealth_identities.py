"""Tests for Amazon stealth browser identities."""
import pytest
from services.amazon_stealth.identities import BrowserIdentity, IDENTITY_PROFILES


class TestBrowserIdentity:
    """Tests for BrowserIdentity dataclass."""

    def test_identity_has_required_fields(self):
        """Identity should have all required browser fingerprint fields."""
        identity = BrowserIdentity(
            id="test_1",
            user_agent="Mozilla/5.0 Test",
            viewport={"width": 1920, "height": 1080},
            timezone="America/New_York",
            locale="en-US",
            color_scheme="light",
            device_scale=1.0,
            webgl_vendor="Test Vendor",
            webgl_renderer="Test Renderer",
        )
        assert identity.id == "test_1"
        assert identity.viewport["width"] == 1920
        assert identity.requests_made == 0
        assert identity.burned_until is None

    def test_identity_pool_has_minimum_profiles(self):
        """Should have at least 10 identity profiles."""
        assert len(IDENTITY_PROFILES) >= 10

    def test_identity_profiles_have_unique_ids(self):
        """All identity profiles should have unique IDs."""
        ids = [p["id"] for p in IDENTITY_PROFILES]
        assert len(ids) == len(set(ids))

    def test_identity_profiles_have_required_fields(self):
        """Each profile should have all required fields."""
        required = ["id", "user_agent", "viewport", "timezone", "locale",
                    "color_scheme", "device_scale", "webgl_vendor", "webgl_renderer"]
        for profile in IDENTITY_PROFILES:
            for field in required:
                assert field in profile, f"Profile {profile.get('id')} missing {field}"
