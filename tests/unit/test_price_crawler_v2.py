"""Tests for Price Crawler V2 features (Caching, Logging)."""
import pytest
from unittest.mock import patch, MagicMock
from services import price_service, price_cache
from models import PriceExtractionLog, db

class TestPriceCrawlerV2:

    def test_cache_hit_avoids_request(self, app):
        """Test that a cache hit returns cached content without network request."""
        url = "https://example.com/product"
        cached_content = "<html>Price: $10.00</html>"
        
        with patch('services.price_cache.get_cached_response', return_value=cached_content) as mock_get_cache:
            with patch('requests.Session.get') as mock_get:
                # Should return CachedResponse
                response = price_service._make_request(url)
                
                assert response.text == cached_content
                assert response.ok is True
                assert response.url == url
                
                # Verify cache was checked
                mock_get_cache.assert_called_once_with(url)
                # Verify network was NOT called
                mock_get.assert_not_called()

    def test_cache_miss_makes_request_and_caches(self, app):
        """Test that a cache miss makes a request and stores result."""
        url = "https://example.com/new"
        content = "<html>Price: $20.00</html>"
        
        with patch('services.price_cache.get_cached_response', return_value=None):
            with patch('services.price_cache.cache_response') as mock_store_cache:
                with patch('requests.Session.get') as mock_get:
                    # Mock network response
                    mock_resp = MagicMock()
                    mock_resp.ok = True
                    mock_resp.text = content
                    mock_resp.raise_for_status = MagicMock()
                    mock_get.return_value = mock_resp
                    
                    response = price_service._make_request(url)
                    
                    assert response.text == content
                    mock_get.assert_called_once()
                    # Verify content was stored
                    mock_store_cache.assert_called_once_with(url, content)

    def test_extraction_logging(self, app):
        """Test that extraction attempts are logged to the database."""
        url = "https://example.com/log-test"
        
        with app.app_context():
            # Run fetch (mocking internal request to avoid network and ensure success)
            # Use a domain that triggers generic price fetching
            with patch('services.price_service._fetch_generic_price', return_value=99.99):
                price = price_service.fetch_price(url)
                assert price == 99.99
                
            # Verify log entry
            log = PriceExtractionLog.query.filter_by(url=url).first()
            assert log is not None
            assert log.success is True
            assert log.price == 99.99
            assert log.domain == "example.com"
            assert log.response_time_ms >= 0

    def test_failed_extraction_logging(self, app):
        """Test that failed extractions are logged with errors."""
        url = "https://example.com/fail-test"
        
        with app.app_context():
             with patch('services.price_service._fetch_generic_price', side_effect=ValueError("Parse Error")):
                price = price_service.fetch_price(url)
                assert price is None
                
             log = PriceExtractionLog.query.filter_by(url=url).first()
             assert log is not None
             assert log.success is False
             assert log.price is None
             assert "Parse Error" in log.error_type
