"""Tests for the price fetching service."""
import datetime
from unittest.mock import patch, MagicMock
import pytest
from app import db, User, Item


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
        from price_service import _parse_price
        assert _parse_price("$19.99") == 19.99
        assert _parse_price("$1,234.56") == 1234.56

    def test_parse_european_format(self):
        """Should parse European format like 19,99"""
        from price_service import _parse_price
        assert _parse_price("19,99") == 19.99

    def test_parse_with_currency_symbols(self):
        """Should strip currency symbols."""
        from price_service import _parse_price
        assert _parse_price("USD 19.99") == 19.99
        assert _parse_price("EUR 19,99") == 19.99

    def test_parse_empty_returns_none(self):
        """Should return None for empty input."""
        from price_service import _parse_price
        assert _parse_price("") is None
        assert _parse_price(None) is None

    def test_parse_invalid_returns_none(self):
        """Should return None for invalid input."""
        from price_service import _parse_price
        assert _parse_price("not a price") is None


class TestFetchPrice:
    """Tests for price fetching functionality."""

    def test_fetch_price_no_url(self):
        """Should return None when URL is empty."""
        from price_service import fetch_price
        assert fetch_price(None) is None
        assert fetch_price("") is None

    @patch('price_service.requests.get')
    def test_fetch_amazon_price(self, mock_get):
        """Should extract price from Amazon page."""
        from price_service import _fetch_amazon_price

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
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        price = _fetch_amazon_price("https://www.amazon.com/dp/B12345")
        assert price == 29.99

    @patch('price_service.requests.get')
    def test_fetch_generic_meta_price(self, mock_get):
        """Should extract price from meta tags."""
        from price_service import fetch_price

        mock_response = MagicMock()
        mock_response.text = '''
        <html>
            <meta property="og:price:amount" content="49.99">
        </html>
        '''
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        price = fetch_price("https://www.example.com/product")
        assert price == 49.99

    @patch('price_service.requests.get')
    def test_fetch_price_handles_network_error(self, mock_get):
        """Should return None on network errors."""
        from price_service import fetch_price
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        price = fetch_price("https://www.amazon.com/dp/B12345")
        assert price is None

    @patch('price_service.requests.get')
    def test_fetch_price_handles_missing_price(self, mock_get):
        """Should return None when price not found on page."""
        from price_service import fetch_price

        mock_response = MagicMock()
        mock_response.text = '<html><body>No price here</body></html>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        price = fetch_price("https://www.example.com/page")
        assert price is None


class TestRefreshItemPrice:
    """Tests for refreshing individual item prices."""

    def test_refresh_price_no_link(self, app, item_owner):
        """Should fail gracefully when item has no link."""
        from price_service import refresh_item_price

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

    @patch('price_service.fetch_price')
    def test_refresh_price_success(self, mock_fetch, app, item_owner):
        """Should update price when fetch succeeds."""
        from price_service import refresh_item_price
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

    @patch('price_service.fetch_price')
    def test_refresh_price_updates_timestamp(self, mock_fetch, app, item_owner):
        """Should update price_updated_at timestamp."""
        from price_service import refresh_item_price
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

    @patch('price_service.fetch_price')
    def test_update_stale_prices_finds_old_items(self, mock_fetch, app, item_owner):
        """Should find items with price_updated_at older than 7 days."""
        from price_service import update_stale_prices

        mock_fetch.return_value = 19.99

        with app.app_context():
            old_date = datetime.datetime.now() - datetime.timedelta(days=10)

            item = Item(
                description="Stale Item",
                user_id=item_owner,
                price=15.00,
                link="https://example.com/product",
                price_updated_at=old_date
            )
            db.session.add(item)
            db.session.commit()

            stats = update_stale_prices(app, db, Item)

            assert stats['items_processed'] == 1
            assert stats['prices_updated'] == 1

    @patch('price_service.fetch_price')
    def test_update_stale_prices_skips_recent(self, mock_fetch, app, item_owner):
        """Should skip items updated recently."""
        from price_service import update_stale_prices

        with app.app_context():
            recent_date = datetime.datetime.now() - datetime.timedelta(days=1)

            item = Item(
                description="Fresh Item",
                user_id=item_owner,
                price=15.00,
                link="https://example.com/product",
                price_updated_at=recent_date
            )
            db.session.add(item)
            db.session.commit()

            stats = update_stale_prices(app, db, Item)

            assert stats['items_processed'] == 0
            mock_fetch.assert_not_called()

    @patch('price_service.fetch_price')
    def test_update_stale_prices_handles_null_date(self, mock_fetch, app, item_owner):
        """Should process items with NULL price_updated_at."""
        from price_service import update_stale_prices

        mock_fetch.return_value = 29.99

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

            stats = update_stale_prices(app, db, Item)

            assert stats['items_processed'] == 1

    @patch('price_service.fetch_price')
    def test_update_stale_prices_handles_errors(self, mock_fetch, app, item_owner):
        """Should handle errors gracefully and continue processing."""
        from price_service import update_stale_prices

        mock_fetch.side_effect = Exception("Fetch error")

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

            stats = update_stale_prices(app, db, Item)

            assert stats['errors'] == 1


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

    @patch('price_service.refresh_item_price')
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
        """Items with links should show Refresh Price button."""
        with app.app_context():
            item = Item(
                description="Linked Item",
                user_id=login_owner,
                link="https://example.com/product"
            )
            db.session.add(item)
            db.session.commit()

        response = client.get('/items')
        assert response.status_code == 200
        assert b'Refresh Price' in response.data
