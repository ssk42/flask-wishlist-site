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
        # @spec AUTO-STL-012
        """Should return a float."""
        result = human_delay(1000)
        assert isinstance(result, float)

    def test_within_variance_range(self):
        # @spec AUTO-STL-012
        """Should be within variance range of base."""
        base_ms = 1000
        variance = 0.3

        results = [human_delay(base_ms, variance) for _ in range(100)]

        min_expected = (base_ms * (1 - variance)) / 1000
        max_expected = (base_ms * (1 + variance)) / 1000

        for result in results:
            assert min_expected <= result <= max_expected

    def test_returns_seconds_not_milliseconds(self):
        # @spec AUTO-STL-012
        """Should return value in seconds."""
        result = human_delay(1000, variance=0)
        assert 0.9 <= result <= 1.1  # ~1 second


class TestBezierPoints:
    """Tests for bezier point generation."""

    def test_returns_list_of_tuples(self):
        # @spec AUTO-STL-009
        """Should return list of (x, y) tuples."""
        points = generate_bezier_points(
            start=(0, 0),
            end=(100, 100),
            num_points=10
        )
        assert isinstance(points, list)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in points)

    def test_starts_and_ends_correctly(self):
        # @spec AUTO-STL-009
        """Should start at start point and end near end point."""
        start = (0, 0)
        end = (100, 100)
        points = generate_bezier_points(start, end, num_points=20)

        assert points[0] == start
        # End point should be close (within noise tolerance)
        assert abs(points[-1][0] - end[0]) < 20
        assert abs(points[-1][1] - end[1]) < 20

    def test_has_correct_number_of_points(self):
        # @spec AUTO-STL-009
        """Should return requested number of points."""
        points = generate_bezier_points((0, 0), (100, 100), num_points=15)
        assert len(points) == 15


class TestCookieSelectors:
    """Tests for cookie banner selectors."""

    def test_has_amazon_selectors(self):
        # @spec AUTO-STL-011
        """Should include Amazon-specific cookie selectors."""
        assert any("sp-cc" in s for s in COOKIE_ACCEPT_SELECTORS)


class TestHumanScroll:
    """Tests for human-like scrolling (variable chunks, random pauses)."""

    @pytest.mark.asyncio
    async def test_scrolls_in_variable_chunks(self):
        # @spec AUTO-STL-010
        from unittest.mock import AsyncMock, patch
        from services.amazon_stealth.behaviors import human_scroll, human_delay

        page = AsyncMock()
        deltas = []

        async def fake_wheel(delta_x, delta_y):
            deltas.append(delta_y)

        page.mouse.wheel = fake_wheel

        with patch("services.amazon_stealth.behaviors.human_delay", return_value=0.001):
            await human_scroll(page, scroll_amount=800)

        # Forward chunks are 50-150; a rare 5%-chance back-scroll is -20..-50.
        # `scrolled` tracks forward movement only, so the forward deltas must sum
        # to at least the target even if one late back-scroll dips net below it.
        assert len(deltas) > 1, "scrolling should happen in several chunks"
        for d in deltas:
            assert (50 <= d <= 150) or (-50 <= d <= -20), f"invalid chunk {d}"
        assert sum(d for d in deltas if d > 0) >= 800, \
            f"forward progress {sum(d for d in deltas if d > 0)} < 800"

    @pytest.mark.asyncio
    async def test_scroll_amount_random_when_unspecified(self):
        from unittest.mock import AsyncMock, patch
        from services.amazon_stealth.behaviors import human_scroll

        page = AsyncMock()
        deltas = []

        async def fake_wheel(delta_x, delta_y):
            deltas.append(delta_y)

        page.mouse.wheel = fake_wheel

        with patch("services.amazon_stealth.behaviors.random.randint") as mock_randint, \
             patch("services.amazon_stealth.behaviors.human_delay", return_value=0.001), \
             patch("services.amazon_stealth.behaviors.random.uniform", return_value=0.1):
            mock_randint.side_effect = [500, 100, 100, 100, 50, 50, 50, 50, 50, 50, 50]
            await human_scroll(page, scroll_amount=None)

        assert sum(deltas) >= 300, "random default amount (300-600) must be honored"
