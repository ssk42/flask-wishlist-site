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
