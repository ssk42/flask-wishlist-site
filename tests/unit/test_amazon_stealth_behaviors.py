"""Tests for Amazon stealth behavior functions."""

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
