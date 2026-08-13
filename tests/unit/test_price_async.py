"""Tests for Async Price Crawler service."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from services import price_async

# Mark all tests in this class as async
@pytest.mark.asyncio
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


@pytest.mark.asyncio
class TestBrowserRescue:
    """Tests for retrying bot-blocked (403/429) URLs through the browser."""

    async def test_403_url_is_rescued_through_browser(self):
        """A 403-blocked URL gets one browser retry and its price is returned;
        a successfully-fetched URL must not be re-fetched."""
        blocked = "https://www.target.com/products/foo"
        ok = "https://www.rei.com/product/bar"

        fake_identity = MagicMock()
        fake_manager = MagicMock()
        fake_manager.get_healthy_identity.return_value = fake_identity

        async def fake_standard(url):
            return (None, 403) if url == blocked else (12.50, 200)

        async def fake_rescue(u, i, m):
            return 9.99

        with patch('services.price_async._fetch_price_async_standard',
                   side_effect=fake_standard), \
             patch('services.price_async._fetch_browser_rescue',
                   side_effect=fake_rescue) as mock_rescue, \
             patch('services.price_async._get_identity_manager',
                   return_value=fake_manager), \
             patch('services.price_metrics.log_extraction_attempt'):

            results = await price_async.fetch_prices_batch([blocked, ok])

        assert results[blocked] == 9.99
        assert results[ok] == 12.50
        # Rescue ran once, only for the blocked URL, using a healthy identity
        assert mock_rescue.await_count == 1
        assert mock_rescue.await_args.args[0] == blocked
        assert mock_rescue.await_args.args[1] is fake_identity

    async def test_no_rescue_for_parse_failure_or_network_error(self):
        """A 200 parse miss and a network error are NOT bot blocks and must
        not be re-fetched through the browser."""
        parse_miss = "https://example.com/noprice"
        net_error = "https://example.com/down"

        async def fake_standard(url):
            if url == parse_miss:
                return None, 200    # page fetched but no price parsed
            return None, None    # network error

        async def fake_rescue(u, i, m):
            return 5.0

        with patch('services.price_async._fetch_price_async_standard',
                   side_effect=fake_standard), \
             patch('services.price_async._fetch_browser_rescue',
                   side_effect=fake_rescue) as mock_rescue, \
             patch('services.price_async._get_identity_manager') as mock_mgr, \
             patch('services.price_metrics.log_extraction_attempt'):

            results = await price_async.fetch_prices_batch([parse_miss, net_error])

        assert results[parse_miss] is None
        assert results[net_error] is None
        mock_rescue.assert_not_called()
        mock_mgr.assert_not_called()  # rescue phase not even entered

    async def test_rescue_disabled_skips_browser(self, monkeypatch):
        """When BROWSER_RESCUE_ENABLED is false, 403 URLs are left as failures
        and the browser is never launched."""
        blocked = "https://www.homedepot.com/p/foo"

        async def fake_standard(url):
            return None, 403

        monkeypatch.setattr(price_async, 'BROWSER_RESCUE_ENABLED', False)

        async def fake_rescue(u, i, m):
            return 5.0

        with patch('services.price_async._fetch_price_async_standard',
                   side_effect=fake_standard), \
             patch('services.price_async._fetch_browser_rescue',
                   side_effect=fake_rescue) as mock_rescue, \
             patch('services.price_async._get_identity_manager') as mock_mgr, \
             patch('services.price_metrics.log_extraction_attempt'):

            results = await price_async.fetch_prices_batch([blocked])

        assert results[blocked] is None
        mock_rescue.assert_not_called()
        mock_mgr.assert_not_called()


class TestRobotBlockDetection:
    """Tests for the anti-bot wall detector used by browser rescue."""

    def test_detects_bot_wall_text(self):
        from services.price_async import _looks_robot_blocked
        assert _looks_robot_blocked("Checking your browser before accessing…")
        assert _looks_robot_blocked("Enter the characters you see to verify you are human")
        assert _looks_robot_blocked("Access Denied - You don't have permission")

    def test_ignores_normal_product_page(self):
        from services.price_async import _looks_robot_blocked
        assert not _looks_robot_blocked(
            "Kindle Paperwhite — $139.99 · In stock · Free shipping")
        assert not _looks_robot_blocked("")
        assert not _looks_robot_blocked(None)
