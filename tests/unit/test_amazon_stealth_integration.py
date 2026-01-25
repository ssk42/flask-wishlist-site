"""Integration tests for Amazon stealth extraction in price service."""
from unittest.mock import MagicMock, patch


class TestAmazonStealthIntegration:
    """Tests for stealth integration in price service."""

    @patch('services.amazon_stealth.stealth_fetch_amazon_sync')
    def test_uses_stealth_when_enabled(self, mock_stealth):
        """Should use stealth extraction when enabled."""
        from services.amazon_stealth import ExtractionResult

        mock_manager = MagicMock()
        mock_identity = MagicMock(id="test")
        mock_manager.get_healthy_identity.return_value = mock_identity

        mock_stealth.return_value = ExtractionResult(success=True, price=29.99)

        with patch('services.price_service.AMAZON_STEALTH_ENABLED', True):
            with patch('services.price_service._get_identity_manager', return_value=mock_manager):
                from services.price_service import _fetch_amazon_price
                result = _fetch_amazon_price("https://amazon.com/dp/B001234")

        assert result == 29.99
        mock_stealth.assert_called_once()
        mock_manager.mark_success.assert_called_once()

    @patch('services.amazon_stealth.stealth_fetch_amazon_sync')
    def test_marks_burned_on_captcha(self, mock_stealth):
        """Should mark identity as burned on CAPTCHA."""
        from services.amazon_stealth import ExtractionResult, AmazonFailureType

        mock_manager = MagicMock()
        identity = MagicMock(id="test")
        mock_manager.get_healthy_identity.return_value = identity

        mock_stealth.return_value = ExtractionResult(
            success=False,
            failure_type=AmazonFailureType.CAPTCHA
        )

        with patch('services.price_service.AMAZON_STEALTH_ENABLED', True):
            with patch('services.price_service._get_identity_manager', return_value=mock_manager):
                from services.price_service import _fetch_amazon_price
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

        from services.price_service import _fetch_amazon_price
        result = _fetch_amazon_price("https://amazon.com/dp/B001234")

        assert result is None

    @patch('services.price_service.AMAZON_STEALTH_ENABLED', False)
    @patch('services.price_service._make_request')
    def test_uses_legacy_when_disabled(self, mock_request):
        """Should use legacy extraction when stealth is disabled."""
        mock_response = MagicMock()
        mock_response.text = '<html><span class="a-price"><span class="a-offscreen">$29.99</span></span></html>'
        mock_request.return_value = mock_response

        from services.price_service import _fetch_amazon_price
        _fetch_amazon_price("https://amazon.com/dp/B001234")

        # Should have called legacy request
        mock_request.assert_called()

    @patch('services.price_service.AMAZON_STEALTH_ENABLED', True)
    @patch('services.price_service._get_identity_manager')
    @patch('services.amazon_stealth.extractor.stealth_fetch_amazon_sync')
    @patch('services.price_service._fetch_amazon_price_legacy')
    def test_falls_back_to_legacy_on_no_manager(
            self, mock_legacy, mock_stealth, mock_get_manager):
        """Should fall back to legacy when identity manager unavailable."""
        mock_get_manager.return_value = None
        mock_legacy.return_value = 19.99

        from services.price_service import _fetch_amazon_price
        result = _fetch_amazon_price("https://amazon.com/dp/B001234")

        # Should fall back to legacy, not use stealth
        mock_stealth.assert_not_called()
        mock_legacy.assert_called_once()
        assert result == 19.99
