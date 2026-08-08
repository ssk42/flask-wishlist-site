# Amazon Stealth Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve Amazon price extraction from ~10% to 50-60% success rate using full stealth Playwright techniques.

**Architecture:** Three-layer approach - Browser Identity Layer (fingerprint rotation), Behavior Layer (human-like interactions), and Request Strategy Layer (identity management, rate limiting). Uses `playwright-stealth` for automation detection evasion.

**Tech Stack:** Python, Playwright, playwright-stealth, Redis (for identity state), pytest

**Design Document:** `docs/plans/2026-01-18-amazon-stealth-design.md`

---

## Task 1: Add Dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Add playwright-stealth to requirements**

Add to `requirements.txt`:
```
playwright-stealth>=1.0.6
```

**Step 2: Install and verify**

Run:
```bash
source venv/bin/activate
pip install playwright-stealth
python -c "from playwright_stealth import stealth_sync; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add playwright-stealth for Amazon extraction"
```

---

## Task 2: Create BrowserIdentity Dataclass

**Files:**
- Create: `services/amazon_stealth/__init__.py`
- Create: `services/amazon_stealth/identities.py`
- Create: `tests/unit/test_amazon_stealth_identities.py`

**Step 1: Create package init**

Create `services/amazon_stealth/__init__.py`:
```python
"""Amazon stealth extraction module."""
from services.amazon_stealth.identities import BrowserIdentity, IDENTITY_PROFILES

__all__ = ['BrowserIdentity', 'IDENTITY_PROFILES']
```

**Step 2: Write failing test for BrowserIdentity**

Create `tests/unit/test_amazon_stealth_identities.py`:
```python
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
```

**Step 3: Run test to verify it fails**

Run:
```bash
pytest tests/unit/test_amazon_stealth_identities.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.amazon_stealth'`

**Step 4: Implement BrowserIdentity and IDENTITY_PROFILES**

Create `services/amazon_stealth/identities.py`:
```python
"""Browser identity profiles for stealth extraction."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BrowserIdentity:
    """Represents a unique browser fingerprint for stealth requests."""

    id: str
    user_agent: str
    viewport: dict
    timezone: str
    locale: str
    color_scheme: str
    device_scale: float
    webgl_vendor: str
    webgl_renderer: str

    # Runtime state (not part of profile definition)
    requests_made: int = field(default=0)
    burned_until: Optional[datetime] = field(default=None)


# Pre-defined identity profiles matching real browser configurations
IDENTITY_PROFILES = [
    {
        "id": "mac_chrome_1",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "viewport": {"width": 1440, "height": 900},
        "timezone": "America/New_York",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 2,
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderer": "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)",
    },
    {
        "id": "mac_chrome_2",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "viewport": {"width": 1680, "height": 1050},
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 2,
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderer": "ANGLE (Apple, Apple M2, OpenGL 4.1)",
    },
    {
        "id": "mac_safari_1",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "viewport": {"width": 1440, "height": 900},
        "timezone": "America/Chicago",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 2,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple M1",
    },
    {
        "id": "windows_chrome_1",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/New_York",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 1,
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070, OpenGL 4.5)",
    },
    {
        "id": "windows_chrome_2",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "viewport": {"width": 2560, "height": 1440},
        "timezone": "America/Denver",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 1,
        "webgl_vendor": "Google Inc. (AMD)",
        "webgl_renderer": "ANGLE (AMD, AMD Radeon RX 6800 XT, OpenGL 4.6)",
    },
    {
        "id": "windows_edge_1",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/Chicago",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 1.25,
        "webgl_vendor": "Google Inc. (Intel)",
        "webgl_renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630, OpenGL 4.6)",
    },
    {
        "id": "windows_firefox_1",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 1,
        "webgl_vendor": "NVIDIA Corporation",
        "webgl_renderer": "NVIDIA GeForce GTX 1660/PCIe/SSE2",
    },
    {
        "id": "linux_chrome_1",
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/New_York",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 1,
        "webgl_vendor": "Google Inc. (NVIDIA Corporation)",
        "webgl_renderer": "ANGLE (NVIDIA Corporation, NVIDIA GeForce RTX 2080/PCIe/SSE2, OpenGL 4.5)",
    },
    {
        "id": "linux_firefox_1",
        "user_agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/Chicago",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 1,
        "webgl_vendor": "AMD",
        "webgl_renderer": "AMD Radeon RX 580 Series (polaris10, LLVM 15.0.7, DRM 3.49, 6.2.0-39-generic)",
    },
    {
        "id": "mac_chrome_3",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "viewport": {"width": 1512, "height": 982},
        "timezone": "America/Phoenix",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 2,
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderer": "ANGLE (Apple, Apple M3 Max, OpenGL 4.1)",
    },
    {
        "id": "windows_chrome_3",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "viewport": {"width": 1366, "height": 768},
        "timezone": "America/New_York",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 1,
        "webgl_vendor": "Google Inc. (Intel)",
        "webgl_renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics, OpenGL 4.6)",
    },
    {
        "id": "mac_safari_2",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        "viewport": {"width": 1280, "height": 800},
        "timezone": "America/Los_Angeles",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 2,
        "webgl_vendor": "Apple Inc.",
        "webgl_renderer": "Apple M2 Pro",
    },
]
```

**Step 5: Run test to verify it passes**

Run:
```bash
pytest tests/unit/test_amazon_stealth_identities.py -v
```

Expected: All 4 tests PASS

**Step 6: Commit**

```bash
git add services/amazon_stealth/ tests/unit/test_amazon_stealth_identities.py
git commit -m "feat(amazon): add BrowserIdentity dataclass and profile pool"
```

---

## Task 3: Create IdentityManager

**Files:**
- Create: `services/amazon_stealth/identity_manager.py`
- Create: `tests/unit/test_amazon_stealth_manager.py`
- Modify: `services/amazon_stealth/__init__.py`

**Step 1: Write failing tests for IdentityManager**

Create `tests/unit/test_amazon_stealth_manager.py`:
```python
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

    def test_get_healthy_identity_returns_none_when_all_burned(self, manager, mock_redis):
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

    def test_get_healthy_identity_prefers_lowest_request_count(self, manager, mock_redis):
        """Should prefer identities with lowest request count."""
        def mock_get(key):
            if "mac_chrome_1:requests" in key:
                return b"5"
            if "mac_chrome_2:requests" in key:
                return b"1"
            return None

        mock_redis.get.side_effect = mock_get

        # Run multiple times, should prefer mac_chrome_2
        identities = [manager.get_healthy_identity() for _ in range(3)]
        ids = [i.id for i in identities]
        assert "mac_chrome_2" in ids
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/unit/test_amazon_stealth_manager.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement IdentityManager**

Create `services/amazon_stealth/identity_manager.py`:
```python
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
```

**Step 4: Update package init**

Update `services/amazon_stealth/__init__.py`:
```python
"""Amazon stealth extraction module."""
from services.amazon_stealth.identities import BrowserIdentity, IDENTITY_PROFILES
from services.amazon_stealth.identity_manager import IdentityManager

__all__ = ['BrowserIdentity', 'IDENTITY_PROFILES', 'IdentityManager']
```

**Step 5: Run test to verify it passes**

Run:
```bash
pytest tests/unit/test_amazon_stealth_manager.py -v
```

Expected: All 7 tests PASS

**Step 6: Commit**

```bash
git add services/amazon_stealth/ tests/unit/test_amazon_stealth_manager.py
git commit -m "feat(amazon): add IdentityManager with Redis persistence"
```

---

## Task 4: Create Behavior Functions

**Files:**
- Create: `services/amazon_stealth/behaviors.py`
- Create: `tests/unit/test_amazon_stealth_behaviors.py`

**Step 1: Write failing tests for behavior functions**

Create `tests/unit/test_amazon_stealth_behaviors.py`:
```python
"""Tests for Amazon stealth behavior functions."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.amazon_stealth.behaviors import (
    human_delay,
    generate_bezier_points,
    COOKIE_ACCEPT_SELECTORS,
)


class TestHumanDelay:
    """Tests for human_delay function."""

    def test_returns_float(self):
        """Should return a float."""
        result = human_delay(1000)
        assert isinstance(result, float)

    def test_within_variance_range(self):
        """Should be within variance range of base."""
        base_ms = 1000
        variance = 0.3

        results = [human_delay(base_ms, variance) for _ in range(100)]

        min_expected = (base_ms * (1 - variance)) / 1000
        max_expected = (base_ms * (1 + variance)) / 1000

        for result in results:
            assert min_expected <= result <= max_expected

    def test_returns_seconds_not_milliseconds(self):
        """Should return value in seconds."""
        result = human_delay(1000, variance=0)
        assert 0.9 <= result <= 1.1  # ~1 second


class TestBezierPoints:
    """Tests for bezier point generation."""

    def test_returns_list_of_tuples(self):
        """Should return list of (x, y) tuples."""
        points = generate_bezier_points(
            start=(0, 0),
            end=(100, 100),
            num_points=10
        )
        assert isinstance(points, list)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in points)

    def test_starts_and_ends_correctly(self):
        """Should start at start point and end near end point."""
        start = (0, 0)
        end = (100, 100)
        points = generate_bezier_points(start, end, num_points=20)

        assert points[0] == start
        # End point should be close (within noise tolerance)
        assert abs(points[-1][0] - end[0]) < 20
        assert abs(points[-1][1] - end[1]) < 20

    def test_has_correct_number_of_points(self):
        """Should return requested number of points."""
        points = generate_bezier_points((0, 0), (100, 100), num_points=15)
        assert len(points) == 15


class TestCookieSelectors:
    """Tests for cookie banner selectors."""

    def test_has_amazon_selectors(self):
        """Should include Amazon-specific cookie selectors."""
        assert any("sp-cc" in s for s in COOKIE_ACCEPT_SELECTORS)
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/unit/test_amazon_stealth_behaviors.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement behavior functions**

Create `services/amazon_stealth/behaviors.py`:
```python
"""Human-like behavior simulation for stealth browsing."""
import asyncio
import random
from typing import List, Tuple

# Amazon cookie accept button selectors
COOKIE_ACCEPT_SELECTORS = [
    "#sp-cc-accept",
    "[data-cel-widget='sp-cc-accept']",
    "input[data-action-type='DISMISS']",
    "#sp-cc-rejectall-link",  # Sometimes we need to reject tracking
]


def human_delay(base_ms: int, variance: float = 0.3) -> float:
    """Generate human-like delay with variance.

    Args:
        base_ms: Base delay in milliseconds
        variance: Variance as percentage (0.3 = +/- 30%)

    Returns:
        Delay in seconds (not milliseconds)
    """
    min_ms = base_ms * (1 - variance)
    max_ms = base_ms * (1 + variance)
    delay_ms = random.uniform(min_ms, max_ms)
    return delay_ms / 1000


def generate_bezier_points(
    start: Tuple[float, float],
    end: Tuple[float, float],
    num_points: int = 20,
    noise: float = 10.0
) -> List[Tuple[float, float]]:
    """Generate points along a bezier curve for natural mouse movement.

    Args:
        start: Starting (x, y) coordinates
        end: Ending (x, y) coordinates
        num_points: Number of points to generate
        noise: Random noise to add to control points

    Returns:
        List of (x, y) coordinates along the curve
    """
    # Generate random control points for bezier curve
    mid_x = (start[0] + end[0]) / 2 + random.uniform(-noise * 3, noise * 3)
    mid_y = (start[1] + end[1]) / 2 + random.uniform(-noise * 3, noise * 3)

    # Control points for quadratic bezier
    control = (mid_x, mid_y)

    points = []
    for i in range(num_points):
        t = i / (num_points - 1)

        # Quadratic bezier formula
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t ** 2 * end[0]
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t ** 2 * end[1]

        # Add small noise except for start point
        if i > 0 and i < num_points - 1:
            x += random.uniform(-noise / 2, noise / 2)
            y += random.uniform(-noise / 2, noise / 2)

        points.append((x, y))

    # Ensure exact start point
    points[0] = start

    return points


async def human_mouse_move(page, target_x: float, target_y: float):
    """Move mouse in a natural curve to target position.

    Args:
        page: Playwright page object
        target_x: Target X coordinate
        target_y: Target Y coordinate
    """
    # Get current mouse position (approximate from viewport center if unknown)
    try:
        current = await page.evaluate("({x: window._mouseX || 640, y: window._mouseY || 400})")
        start = (current['x'], current['y'])
    except Exception:
        start = (640, 400)  # Default to viewport center

    # Generate curved path
    points = generate_bezier_points(start, (target_x, target_y), num_points=random.randint(15, 25))

    # Move through points
    for x, y in points:
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.005, 0.025))

    # Track position for next move
    await page.evaluate(f"window._mouseX = {target_x}; window._mouseY = {target_y}")


async def human_scroll(page, scroll_amount: int = None):
    """Scroll page in a human-like manner.

    Args:
        page: Playwright page object
        scroll_amount: Total amount to scroll (random if None)
    """
    if scroll_amount is None:
        scroll_amount = random.randint(300, 600)

    scrolled = 0
    while scrolled < scroll_amount:
        # Variable scroll chunk
        chunk = random.randint(50, 150)
        await page.mouse.wheel(0, chunk)
        scrolled += chunk

        # Random pause
        await asyncio.sleep(human_delay(300, 0.5))

        # Occasionally scroll back slightly (5% chance)
        if random.random() < 0.05:
            back = random.randint(20, 50)
            await page.mouse.wheel(0, -back)
            await asyncio.sleep(human_delay(200, 0.3))


async def handle_cookie_banner(page) -> bool:
    """Attempt to accept/dismiss cookie banner.

    Args:
        page: Playwright page object

    Returns:
        True if banner was handled, False otherwise
    """
    for selector in COOKIE_ACCEPT_SELECTORS:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                # Wait a bit like a human would
                await asyncio.sleep(human_delay(500, 0.3))
                await elem.click()
                await asyncio.sleep(human_delay(300, 0.2))
                return True
        except Exception:
            continue
    return False


async def interact_like_human(page):
    """Simulate human browsing behavior before extracting data.

    Args:
        page: Playwright page object
    """
    # 1. Wait after page load (reading time)
    await asyncio.sleep(human_delay(1000, 0.4))

    # 2. Handle cookie banner if present
    await handle_cookie_banner(page)

    # 3. Move mouse to neutral area
    viewport = page.viewport_size or {"width": 1280, "height": 800}
    await human_mouse_move(
        page,
        random.randint(int(viewport["width"] * 0.3), int(viewport["width"] * 0.7)),
        random.randint(int(viewport["height"] * 0.2), int(viewport["height"] * 0.4))
    )

    # 4. Scroll down to product area
    await human_scroll(page, random.randint(200, 400))

    # 5. Move mouse near price area (common Amazon layout)
    await human_mouse_move(
        page,
        random.randint(300, 500),
        random.randint(300, 500)
    )

    # 6. Brief pause before extraction
    await asyncio.sleep(human_delay(500, 0.3))
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/unit/test_amazon_stealth_behaviors.py -v
```

Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add services/amazon_stealth/behaviors.py tests/unit/test_amazon_stealth_behaviors.py
git commit -m "feat(amazon): add human-like behavior simulation functions"
```

---

## Task 5: Create Stealth Extractor

**Files:**
- Create: `services/amazon_stealth/extractor.py`
- Create: `tests/unit/test_amazon_stealth_extractor.py`
- Modify: `services/amazon_stealth/__init__.py`

**Step 1: Write failing tests for extractor**

Create `tests/unit/test_amazon_stealth_extractor.py`:
```python
"""Tests for Amazon stealth extractor."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from services.amazon_stealth.extractor import (
    ExtractionResult,
    AmazonFailureType,
    classify_failure,
)


class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""

    def test_success_result(self):
        """Should create successful result with price."""
        result = ExtractionResult(success=True, price=29.99)
        assert result.success is True
        assert result.price == 29.99
        assert result.failure_type is None

    def test_failure_result(self):
        """Should create failure result with type."""
        result = ExtractionResult(
            success=False,
            failure_type=AmazonFailureType.CAPTCHA
        )
        assert result.success is False
        assert result.price is None
        assert result.failure_type == AmazonFailureType.CAPTCHA


class TestClassifyFailure:
    """Tests for failure classification."""

    def test_detects_captcha(self):
        """Should detect CAPTCHA pages."""
        content = "<html><body>Please complete the CAPTCHA below</body></html>"
        result = classify_failure(content, 200)
        assert result == AmazonFailureType.CAPTCHA

    def test_detects_robot_check(self):
        """Should detect robot check pages."""
        content = "<html><body>Robot Check - verify you are human</body></html>"
        result = classify_failure(content, 200)
        assert result == AmazonFailureType.CAPTCHA

    def test_detects_rate_limit(self):
        """Should detect rate limiting."""
        result = classify_failure("<html></html>", 429)
        assert result == AmazonFailureType.RATE_LIMITED

    def test_detects_blocked(self):
        """Should detect 503 as rate limited."""
        result = classify_failure("<html></html>", 503)
        assert result == AmazonFailureType.RATE_LIMITED

    def test_no_price_found(self):
        """Should return NO_PRICE_FOUND for normal pages without price."""
        result = classify_failure("<html><body>Normal page</body></html>", 200)
        assert result == AmazonFailureType.NO_PRICE_FOUND
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/unit/test_amazon_stealth_extractor.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement stealth extractor**

Create `services/amazon_stealth/extractor.py`:
```python
"""Stealth extraction for Amazon prices."""
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from bs4 import BeautifulSoup

from services.amazon_stealth.identities import BrowserIdentity
from services.amazon_stealth.behaviors import interact_like_human, handle_cookie_banner

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
        from playwright_stealth import stealth_async
    except ImportError:
        logger.error("playwright-stealth not installed")
        return ExtractionResult(
            success=False,
            failure_type=AmazonFailureType.NETWORK_ERROR
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
            await stealth_async(page)

            # Navigate with timeout
            try:
                response = await page.goto(
                    url,
                    timeout=30000,
                    wait_until='domcontentloaded'
                )
                status_code = response.status if response else 0
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
            if 'captcha' in content.lower() or 'robot check' in content.lower():
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
                return ExtractionResult(success=True, price=price, content=content)
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
```

**Step 4: Update package init**

Update `services/amazon_stealth/__init__.py`:
```python
"""Amazon stealth extraction module."""
from services.amazon_stealth.identities import BrowserIdentity, IDENTITY_PROFILES
from services.amazon_stealth.identity_manager import IdentityManager
from services.amazon_stealth.extractor import (
    ExtractionResult,
    AmazonFailureType,
    stealth_fetch_amazon,
    stealth_fetch_amazon_sync,
)

__all__ = [
    'BrowserIdentity',
    'IDENTITY_PROFILES',
    'IdentityManager',
    'ExtractionResult',
    'AmazonFailureType',
    'stealth_fetch_amazon',
    'stealth_fetch_amazon_sync',
]
```

**Step 5: Run test to verify it passes**

Run:
```bash
pytest tests/unit/test_amazon_stealth_extractor.py -v
```

Expected: All 7 tests PASS

**Step 6: Commit**

```bash
git add services/amazon_stealth/ tests/unit/test_amazon_stealth_extractor.py
git commit -m "feat(amazon): add stealth extractor with failure classification"
```

---

## Task 6: Integrate with Price Service

**Files:**
- Modify: `services/price_service.py`
- Create: `tests/unit/test_amazon_stealth_integration.py`

**Step 1: Write integration test**

Create `tests/unit/test_amazon_stealth_integration.py`:
```python
"""Integration tests for Amazon stealth extraction in price service."""
import pytest
from unittest.mock import MagicMock, patch

from services.price_service import _fetch_amazon_price


class TestAmazonStealthIntegration:
    """Tests for stealth integration in price service."""

    @patch('services.price_service.AMAZON_STEALTH_ENABLED', True)
    @patch('services.price_service._get_identity_manager')
    @patch('services.amazon_stealth.extractor.stealth_fetch_amazon_sync')
    def test_uses_stealth_when_enabled(self, mock_stealth, mock_get_manager):
        """Should use stealth extraction when enabled."""
        from services.amazon_stealth import ExtractionResult

        mock_manager = MagicMock()
        mock_manager.get_healthy_identity.return_value = MagicMock(id="test")
        mock_get_manager.return_value = mock_manager

        mock_stealth.return_value = ExtractionResult(success=True, price=29.99)

        result = _fetch_amazon_price("https://amazon.com/dp/B001234")

        assert result == 29.99
        mock_stealth.assert_called_once()
        mock_manager.mark_success.assert_called_once()

    @patch('services.price_service.AMAZON_STEALTH_ENABLED', True)
    @patch('services.price_service._get_identity_manager')
    @patch('services.amazon_stealth.extractor.stealth_fetch_amazon_sync')
    def test_marks_burned_on_captcha(self, mock_stealth, mock_get_manager):
        """Should mark identity as burned on CAPTCHA."""
        from services.amazon_stealth import ExtractionResult, AmazonFailureType

        mock_manager = MagicMock()
        identity = MagicMock(id="test")
        mock_manager.get_healthy_identity.return_value = identity
        mock_get_manager.return_value = mock_manager

        mock_stealth.return_value = ExtractionResult(
            success=False,
            failure_type=AmazonFailureType.CAPTCHA
        )

        result = _fetch_amazon_price("https://amazon.com/dp/B001234")

        assert result is None
        mock_manager.mark_burned.assert_called_once_with(identity)

    @patch('services.price_service.AMAZON_STEALTH_ENABLED', True)
    @patch('services.price_service._get_identity_manager')
    def test_skips_when_all_identities_burned(self, mock_get_manager):
        """Should skip extraction when all identities are burned."""
        mock_manager = MagicMock()
        mock_manager.get_healthy_identity.return_value = None
        mock_get_manager.return_value = mock_manager

        result = _fetch_amazon_price("https://amazon.com/dp/B001234")

        assert result is None

    @patch('services.price_service.AMAZON_STEALTH_ENABLED', False)
    @patch('services.price_service._make_request')
    def test_uses_legacy_when_disabled(self, mock_request):
        """Should use legacy extraction when stealth is disabled."""
        mock_response = MagicMock()
        mock_response.text = '<html><span class="a-price"><span class="a-offscreen">$29.99</span></span></html>'
        mock_request.return_value = mock_response

        result = _fetch_amazon_price("https://amazon.com/dp/B001234")

        # Should have called legacy request
        mock_request.assert_called()
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/unit/test_amazon_stealth_integration.py -v
```

Expected: FAIL (AMAZON_STEALTH_ENABLED not defined)

**Step 3: Modify price_service.py to integrate stealth extraction**

Add to top of `services/price_service.py` after imports:
```python
# Feature flag for stealth extraction
AMAZON_STEALTH_ENABLED = True

# Singleton identity manager (lazy initialized)
_identity_manager = None

def _get_identity_manager():
    """Get or create the identity manager singleton."""
    global _identity_manager
    if _identity_manager is None:
        try:
            from extensions import redis_client
            from services.amazon_stealth import IdentityManager
            _identity_manager = IdentityManager(redis_client)
        except Exception as e:
            logger.warning(f"Could not initialize IdentityManager: {e}")
            return None
    return _identity_manager
```

Replace the `_fetch_amazon_price` function:
```python
def _fetch_amazon_price(url):
    """Fetch price from Amazon product page.

    Uses stealth Playwright when enabled, falls back to legacy extraction.
    """
    # Try stealth extraction if enabled
    if AMAZON_STEALTH_ENABLED:
        manager = _get_identity_manager()
        if manager:
            identity = manager.get_healthy_identity()
            if identity:
                try:
                    from services.amazon_stealth import (
                        stealth_fetch_amazon_sync,
                        AmazonFailureType,
                    )

                    result = stealth_fetch_amazon_sync(url, identity, manager)

                    if result.success:
                        manager.mark_success(identity)
                        return result.price
                    elif result.failure_type == AmazonFailureType.CAPTCHA:
                        manager.mark_burned(identity)
                        logger.warning(f"Amazon CAPTCHA, burned identity {identity.id}")
                    elif result.failure_type == AmazonFailureType.RATE_LIMITED:
                        logger.warning(f"Amazon rate limited, backing off")

                    return None

                except Exception as e:
                    logger.error(f"Stealth extraction error: {e}")
            else:
                logger.warning("All Amazon identities burned, skipping")
                return None

    # Legacy extraction (disabled when stealth is enabled)
    try:
        session = _get_session()
        session.headers.update({
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.amazon.com/',
            'DNT': '1',
        })

        response = _make_request(url, session)
        if not response:
            logger.warning(f'Amazon request failed (possible bot detection): {url}')
            return None

        if 'captcha' in response.text.lower() or 'robot check' in response.text.lower():
            logger.warning(f'Amazon returned CAPTCHA/robot check page: {url}')
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        return _extract_amazon_price_from_soup(soup)
    except Exception as e:
        logger.warning(f'Amazon price fetch failed for {url}: {str(e)}')
        return None
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/unit/test_amazon_stealth_integration.py -v
```

Expected: All 4 tests PASS

**Step 5: Run full test suite to ensure no regressions**

Run:
```bash
pytest tests/unit/ -v --tb=short
```

Expected: All tests PASS

**Step 6: Commit**

```bash
git add services/price_service.py tests/unit/test_amazon_stealth_integration.py
git commit -m "feat(amazon): integrate stealth extraction into price service"
```

---

## Task 7: Add Monitoring & Feature Flag Config

**Files:**
- Modify: `services/price_metrics.py`
- Modify: `config.py`

**Step 1: Add stealth-specific metrics to price_metrics.py**

Add to `services/price_metrics.py`:
```python
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
```

**Step 2: Add feature flag to config.py**

Add to `config.py`:
```python
# Amazon stealth extraction settings
AMAZON_STEALTH_ENABLED = os.environ.get('AMAZON_STEALTH_ENABLED', 'true').lower() == 'true'
```

**Step 3: Update price_service.py to use config**

Update top of `services/price_service.py`:
```python
from config import AMAZON_STEALTH_ENABLED
```

Remove the hardcoded `AMAZON_STEALTH_ENABLED = True` line.

**Step 4: Run tests**

Run:
```bash
pytest tests/unit/ -v --tb=short
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add services/price_metrics.py config.py services/price_service.py
git commit -m "feat(amazon): add stealth metrics logging and config flag"
```

---

## Task 8: Final Integration Test & Documentation

**Files:**
- Modify: `CLAUDE.md` (add documentation)
- Run full test suite

**Step 1: Run full test suite**

Run:
```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS with >90% coverage

**Step 2: Update CLAUDE.md with feature documentation**

Add to CLAUDE.md under "### Key Features & Behaviors":
```markdown
#### Amazon Stealth Extraction
The application uses stealth Playwright techniques for Amazon price extraction:
- **Browser Identity Rotation**: 12 realistic browser profiles rotated every 10-20 requests
- **Human-like Behavior**: Mouse movements, scrolling, natural delays
- **Identity Burn Tracking**: Identities that trigger CAPTCHA are disabled for 24 hours
- **Feature Flag**: Controlled via `AMAZON_STEALTH_ENABLED` environment variable
- **Implementation**: `services/amazon_stealth/` module
```

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Amazon stealth extraction documentation"
```

**Step 4: Final verification**

Run:
```bash
pytest tests/ --cov --cov-report=term-missing
git log --oneline -10
```

Verify: All tests pass, coverage >90%, commits are clean.

---

## Summary

| Task | Description | Files | Estimated Time |
|------|-------------|-------|----------------|
| 1 | Add dependencies | requirements.txt | 5 min |
| 2 | BrowserIdentity dataclass | identities.py, tests | 20 min |
| 3 | IdentityManager | identity_manager.py, tests | 30 min |
| 4 | Behavior functions | behaviors.py, tests | 30 min |
| 5 | Stealth extractor | extractor.py, tests | 30 min |
| 6 | Price service integration | price_service.py, tests | 30 min |
| 7 | Monitoring & config | price_metrics.py, config.py | 15 min |
| 8 | Final integration | CLAUDE.md, full tests | 20 min |

**Total Estimated Time:** ~3 hours (excluding manual testing with real Amazon URLs)
