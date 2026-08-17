"""Tests for the price fetching service."""
import datetime
from unittest.mock import patch, MagicMock
import pytest
from models import db, User, Item


@pytest.fixture
def item_owner(app):
    """Create a user who owns items."""
    with app.app_context():
        user = User(name="Owner", email="owner@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def login_owner(client, item_owner):
    """Log in as the item owner."""
    with client.session_transaction() as session:
        session["_user_id"] = str(item_owner)
        session["_fresh"] = True
    return item_owner


class TestPriceParser:
    """Tests for price parsing functionality."""

    def test_parse_us_dollar_format(self):
        """Should parse US dollar format like $19.99"""
        from services.price_extraction.parser import parse_price as _parse_price
        assert _parse_price("$19.99") == 19.99
        assert _parse_price("$1,234.56") == 1234.56

    def test_parse_european_format(self):
        """Should parse European format like 19,99"""
        from services.price_extraction.parser import parse_price as _parse_price
        assert _parse_price("19,99") == 19.99

    def test_parse_with_currency_symbols(self):
        """Should strip currency symbols."""
        from services.price_extraction.parser import parse_price as _parse_price
        assert _parse_price("USD 19.99") == 19.99
        assert _parse_price("EUR 19,99") == 19.99

    def test_parse_empty_returns_none(self):
        """Should return None for empty input."""
        from services.price_extraction.parser import parse_price as _parse_price
        assert _parse_price("") is None
        assert _parse_price(None) is None

    def test_parse_invalid_returns_none(self):
        """Should return None for invalid input."""
        from services.price_extraction.parser import parse_price as _parse_price
        assert _parse_price("not a price") is None


class TestFetchPrice:
    """Tests for price fetching functionality."""

    def test_fetch_price_no_url(self):
        """Should return None when URL is empty."""
        from services.price_service import fetch_price
        assert fetch_price(None) is None
        assert fetch_price("") is None

    @patch('services.price_service._get_identity_manager')
    @patch('services.price_service._make_request')
    def test_fetch_amazon_price(self, mock_request, mock_identity_mgr):
        """Should extract price from Amazon page."""
        from services.price_service import _fetch_amazon_price

        # Mock identity manager to return None (skip stealth mode)
        mock_identity_mgr.return_value = None

        mock_response = MagicMock()
        # More complete HTML with proper Amazon price structure
        mock_response.text = '''
        <html>
        <body>
            <div id="corePrice_feature_div">
                <span class="a-offscreen">$29.99</span>
            </div>
        </body>
        </html>
        '''
        mock_request.return_value = mock_response

        price = _fetch_amazon_price("https://www.amazon.com/dp/B12345")
        assert price == 29.99

    @patch('services.price_service._make_request')
    def test_fetch_generic_meta_price(self, mock_request):
        # @spec AUTO-PRC-008
        """Should extract price from meta tags."""
        from services.price_service import fetch_price

        mock_response = MagicMock()
        mock_response.text = '''
        <html>
            <meta property="og:price:amount" content="49.99">
        </html>
        '''
        mock_request.return_value = mock_response

        price = fetch_price("https://www.example.com/product")
        assert price == 49.99

    @patch('services.price_service._make_request')
    def test_fetch_price_handles_network_error(self, mock_request):
        """Should return None on network errors."""
        from services.price_service import fetch_price

        mock_request.return_value = None

        price = fetch_price("https://www.amazon.com/dp/B12345")
        assert price is None

    @patch('services.price_service._make_request')
    def test_fetch_price_handles_missing_price(self, mock_request):
        """Should return None when price not found on page."""
        from services.price_service import fetch_price

        mock_response = MagicMock()
        mock_response.text = '<html><body>No price here</body></html>'
        mock_request.return_value = mock_response

        price = fetch_price("https://www.example.com/page")
        assert price is None


class TestRefreshItemPrice:
    """Tests for refreshing individual item prices."""

    def test_refresh_price_no_link(self, app, item_owner):
        """Should fail gracefully when item has no link."""
        from services.price_service import refresh_item_price

        with app.app_context():
            item = Item(
                description="No Link Item",
                user_id=item_owner,
                price=10.00
            )
            db.session.add(item)
            db.session.commit()

            success, new_price, message = refresh_item_price(item, db)

            assert success is False
            assert new_price is None
            assert 'no link' in message.lower()

    @patch('services.price_service.fetch_price')
    def test_refresh_price_success(self, mock_fetch, app, item_owner):
        """Should update price when fetch succeeds."""
        from services.price_service import refresh_item_price
        mock_fetch.return_value = 39.99

        with app.app_context():
            item = Item(
                description="Test Item",
                user_id=item_owner,
                price=29.99,
                link="https://example.com/product"
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

            success, new_price, message = refresh_item_price(item, db)

            assert success is True
            assert new_price == 39.99

            # Verify database was updated
            updated_item = db.session.get(Item, item_id)
            assert updated_item.price == 39.99
            assert updated_item.price_updated_at is not None

    @patch('services.price_service.fetch_price')
    def test_refresh_price_updates_timestamp(self, mock_fetch, app, item_owner):
        """Should update price_updated_at timestamp."""
        from services.price_service import refresh_item_price
        mock_fetch.return_value = 25.00

        with app.app_context():
            item = Item(
                description="Test Item",
                user_id=item_owner,
                price=25.00,
                link="https://example.com/product"
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

            refresh_item_price(item, db)

            updated_item = db.session.get(Item, item_id)
            assert updated_item.price_updated_at is not None


class TestUpdateStalePrices:
    """Tests for the batch price update function."""

    def test_update_stale_prices_finds_old_items(self, app, item_owner):
        # @spec AUTO-PRC-006
        """Should find items with price_updated_at older than 7 days."""
        from services.price_service import update_stale_prices

        with app.app_context():
            old_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)

            item = Item(
                description="Stale Item",
                user_id=item_owner,
                price=15.00,
                link="https://example.com/product",
                price_updated_at=old_date
            )
            db.session.add(item)
            db.session.commit()

            with patch('asyncio.run') as mock_asyncio_run:
                # Mock returns dict of url -> price
                mock_asyncio_run.return_value = {"https://example.com/product": 19.99}

                stats = update_stale_prices(app, db, Item)

                assert stats['items_processed'] == 1
                assert stats['prices_updated'] == 1

    def test_update_stale_prices_skips_recent(self, app, item_owner):
        # @spec AUTO-PRC-006
        """Should skip items updated recently."""
        from services.price_service import update_stale_prices

        with app.app_context():
            recent_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)

            item = Item(
                description="Fresh Item",
                user_id=item_owner,
                price=15.00,
                link="https://example.com/product",
                price_updated_at=recent_date
            )
            db.session.add(item)
            db.session.commit()

            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.side_effect = lambda coro: (coro.close(), {})[1]
                stats = update_stale_prices(app, db, Item)

                assert stats['items_processed'] == 0
                mock_asyncio_run.assert_not_called()

    def test_update_stale_prices_handles_null_date(self, app, item_owner):
        # @spec AUTO-PRC-006
        """Should process items with NULL price_updated_at."""
        from services.price_service import update_stale_prices

        with app.app_context():
            item = Item(
                description="Never Updated Item",
                user_id=item_owner,
                price=25.00,
                link="https://example.com/product",
                price_updated_at=None
            )
            db.session.add(item)
            db.session.commit()

            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.side_effect = lambda coro: (coro.close(), {"https://example.com/product": 29.99})[1]

                stats = update_stale_prices(app, db, Item)

                assert stats['items_processed'] == 1

    def test_update_stale_prices_timestamps_failed_url(self, app, item_owner):
        # @spec AUTO-PRC-007
        """A URL that fails during a batch update must get a fresh price_updated_at
        so it is not retried immediately on the next run."""
        from services.price_service import update_stale_prices

        with app.app_context():
            item = Item(
                description="Failing Item",
                user_id=item_owner,
                price=10.00,
                link="https://example.com/doomed",
                price_updated_at=None
            )
            db.session.add(item)
            db.session.commit()

            with patch('asyncio.run') as mock_asyncio_run:
                # The URL is in the item set but ABSENT from results → it failed.
                # Close the discarded coroutine so pytest doesn't warn about it.
                def run_and_close(coro):
                    coro.close()
                    return {}
                mock_asyncio_run.side_effect = run_and_close

                before = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                stats = update_stale_prices(app, db, Item)

            assert stats['errors'] == 1
            # Fresh query (not the identity-map object created above) must show
            # the failure timestamp was written at/after this batch ran.
            updated = db.session.execute(
                db.select(Item).where(Item.id == item.id)
            ).scalar_one()
            assert updated.price_updated_at is not None
            assert updated.price_updated_at >= before


    def test_update_stale_prices_handles_errors(self, app, item_owner):
        # @spec AUTO-PRC-006
        """Should handle errors gracefully and continue processing."""
        from services.price_service import update_stale_prices

        with app.app_context():
            item = Item(
                description="Error Item",
                user_id=item_owner,
                price=25.00,
                link="https://example.com/product",
                price_updated_at=None
            )
            db.session.add(item)
            db.session.commit()

            with patch('asyncio.run') as mock_asyncio_run:
                # Mock raises exception after closing coroutine
                def mock_run(coro):
                    coro.close()
                    raise Exception("Batch fetch error")
                mock_asyncio_run.side_effect = mock_run

                stats = update_stale_prices(app, db, Item)

                # When batch fetch fails entirely, all items are marked as errors
                assert stats['errors'] >= 1

    def test_failed_fetch_is_retry_paced_not_stamped_fresh(self, app, item_owner):
        """A fetch that returns no price must be stamped ~6 days old so it retries
        in about a day (7-day staleness window), not treated as freshly updated
        (which would shelve it for a full week)."""
        from services.price_service import update_stale_prices

        with app.app_context():
            item = Item(
                description="Fail Item",
                user_id=item_owner,
                price=25.00,
                link="https://example.com/product",
                price_updated_at=None
            )
            db.session.add(item)
            db.session.commit()
            now = datetime.datetime.now(datetime.timezone.utc)

            with patch('asyncio.run') as mock_asyncio_run:
                # Fetch completes but returns no price for the URL
                mock_asyncio_run.return_value = {"https://example.com/product": None}
                update_stale_prices(app, db, Item)

                item = db.session.get(Item, item.id)
                assert item.price_updated_at is not None
                # SQLite round-trips naive datetimes; compare on naive clocks
                age = now.replace(tzinfo=None) - item.price_updated_at
                # ~6 days old: within 7-day stale window so it retries ~daily
                assert datetime.timedelta(days=5.5) < age < datetime.timedelta(days=6.5)
                # Price must be untouched
                assert item.price == 25.00


class TestRefreshPriceRoute:
    """Tests for the /item/<id>/refresh-price route."""

    def test_refresh_price_requires_auth(self, client):
        """Refresh price should require authentication."""
        response = client.post('/item/1/refresh-price')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_refresh_price_404_for_missing(self, client, login_owner):
        """Should return 404 for non-existent item."""
        response = client.post('/item/99999/refresh-price')
        assert response.status_code == 404

    def test_refresh_price_warning_no_link(self, app, client, login_owner):
        """Should show warning when item has no link."""
        with app.app_context():
            item = Item(
                description="No Link",
                user_id=login_owner
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        response = client.post(f'/item/{item_id}/refresh-price', follow_redirects=True)
        assert response.status_code == 200
        assert b'no link' in response.data.lower()

    @patch('services.price_service.refresh_item_price')
    def test_refresh_price_success(self, mock_refresh, app, client, login_owner):
        """Should show success message when price is updated."""
        mock_refresh.return_value = (True, 49.99, "Price updated")

        with app.app_context():
            item = Item(
                description="Test Item",
                user_id=login_owner,
                link="https://example.com/product"
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        response = client.post(f'/item/{item_id}/refresh-price', follow_redirects=True)
        assert response.status_code == 200


class TestPriceDisplayInUI:
    """Tests for price display in templates."""

    def test_items_list_shows_price_date(self, app, client, login_owner):
        """Items list should show 'Price as of' when price_updated_at is set."""
        with app.app_context():
            item = Item(
                description="Priced Item",
                user_id=login_owner,
                price=25.00,
                price_updated_at=datetime.datetime(2025, 1, 15)
            )
            db.session.add(item)
            db.session.commit()

        response = client.get('/items')
        assert response.status_code == 200
        assert b'25.00' in response.data
        assert b'Jan 15' in response.data

    def test_items_list_shows_refresh_button(self, app, client, login_owner):
        """Items with links and price should show Refresh Price button."""
        with app.app_context():
            item = Item(
                description="Linked Item",
                user_id=login_owner,
                link="https://example.com/product",
                price=29.99
            )
            db.session.add(item)
            db.session.commit()

        response = client.get('/items')
        assert response.status_code == 200
        assert b'Refresh Price' in response.data
