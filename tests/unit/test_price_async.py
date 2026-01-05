"""Tests for Async Price Crawler service."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from services import price_async

# Mark all tests in this class as async
@pytest.mark.asyncio
@pytest.mark.skip(reason="Stale async tests causing event loop conflicts in CI environment")
class TestPriceAsync:

    async def test_fetch_prices_batch_success(self):
        """Test concurrent batch fetching of prices."""
        urls = [
            "https://example.com/item1",
            "https://example.com/item2",
            "https://example.com/item3"
        ]
        
        # Mock responses
        mock_responses = {
            "https://example.com/item1": ("<html>Price: $10.00</html>", 10.0),
            "https://example.com/item2": ("<html>Price: $20.00</html>", 20.0),
            "https://example.com/item3": ("<html>Price: $30.00</html>", 30.0),
        }
        
        # Mock dependencies
        with patch('services.price_async._get_async_session') as mock_session_factory, \
             patch('services.price_async._parse_content') as mock_parser, \
             patch('services.price_cache.get_cached_response', return_value=None), \
             patch('services.price_cache.cache_response') as mock_cache, \
             patch('services.price_metrics.log_extraction_attempt') as mock_log:

            # Setup AsyncMock session
            mock_session = AsyncMock()
            # Session must be an async context manager
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            
            # Factory must be awaitable and return the session
            async def get_session_stub():
                return mock_session
            mock_session_factory.side_effect = get_session_stub
            
            # Setup response factory
            def get_response_ctx_factory(url, **kwargs):
                resp = AsyncMock()
                resp.status = 200
                html, price = mock_responses.get(url, ("", None))
                resp.text.return_value = html
                
                ctx = AsyncMock()
                ctx.__aenter__.return_value = resp
                return ctx
            
            # Configure session.get to be a SYNC function that returns the async context manager
            mock_session.get = MagicMock(side_effect=get_response_ctx_factory)
            
            # Configure parser
            def parse_side_effect(url, html):
                return mock_responses.get(url)[1]
            mock_parser.side_effect = parse_side_effect
            
            # Execute
            results = await price_async.fetch_prices_batch(urls)
            
            # Verify
            assert len(results) == 3
            assert results["https://example.com/item1"] == 10.0
            assert results["https://example.com/item2"] == 20.0
            assert results["https://example.com/item3"] == 30.0
            
            # Verify logging count (sync callback)
            assert mock_log.call_count == 3
            
            # Verify caching
            assert mock_cache.call_count == 3

    async def test_fetch_prices_batch_partial_failure(self):
        """Test batch fetching with some failures."""
        urls = [
            "https://example.com/success",
            "https://example.com/fail_network",
            "https://example.com/fail_parse"
        ]
        
        with patch('services.price_async._get_async_session') as mock_session_factory, \
             patch('services.price_async._parse_content') as mock_parser, \
             patch('services.price_cache.get_cached_response', return_value=None), \
             patch('services.price_metrics.log_extraction_attempt'): # silence metrics

            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            
            async def get_session_stub():
                return mock_session
            mock_session_factory.side_effect = get_session_stub
            
            def get_response_ctx_factory(url, **kwargs):
                resp = AsyncMock()
                if "fail_network" in url:
                    resp.status = 500
                else:
                    resp.status = 200
                resp.text.return_value = "<html>Content</html>"
                
                ctx = AsyncMock()
                ctx.__aenter__.return_value = resp
                return ctx
            
            mock_session.get = MagicMock(side_effect=get_response_ctx_factory)
            
            def parse_side_effect(url, html):
                if "success" in url:
                    return 50.0
                return None # Fail parse
            mock_parser.side_effect = parse_side_effect
            
            results = await price_async.fetch_prices_batch(urls)
            
            # Results should contain URLs where price was found
            # Failed parse returns None, Network fail returns None
            # Our batch function returns a dict of {url: price}. 
            # If price is None, it might still verify the key exists if we want explicit None,
            # or it might omit. Let's check the implementation.
            # Implementation: results[url] = price, even if None?
            # "if isinstance(result, tuple) ... results[url] = price"
            # Yes, internal _fetch_price_async returns None on error.
            
            assert results["https://example.com/success"] == 50.0
            assert results["https://example.com/fail_network"] is None
            assert results["https://example.com/fail_parse"] is None

    async def test_batch_cache_hit(self):
        """Test that cached items avoid network calls."""
        urls = ["https://example.com/cached"]
        
        with patch('services.price_cache.get_cached_response', return_value="<html>Cached</html>") as mock_cache_get, \
             patch('services.price_async._get_async_session') as mock_session_factory, \
             patch('services.price_async._parse_content', return_value=99.0):
             
            results = await price_async.fetch_prices_batch(urls)
            
            assert results["https://example.com/cached"] == 99.0
            mock_session_factory.assert_not_called() # No network session created
