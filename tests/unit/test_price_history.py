import pytest
from datetime import datetime, timedelta, timezone
from models import PriceHistory, Item, User
from services.price_history import record_price_history, get_price_history_stats
from app import db


class TestPriceHistory:
    @pytest.fixture(autouse=True)
    def setup(self, app):
        self.app = app
        self.db = db

        # Create test user and item
        with self.app.app_context():
            user = User(
                name='HistoryTestUser',
                email='history@test.com',
                is_private=False)
            self.db.session.add(user)
            self.db.session.commit()
            self.user_id = user.id

            # Use instance attribute to properly store the item ID for
            # retrieval later
            new_item = Item(
                description='Test Item',
                user_id=user.id,
                price=100.0)
            self.db.session.add(new_item)
            self.db.session.commit()
            self.item_id = new_item.id

    def test_record_price_history_initial(self):
        """Test recording initial price history."""
        with self.app.app_context():
            result = record_price_history(
                self.item_id, 100.0, source='initial')

            assert result is True
            history = PriceHistory.query.filter_by(item_id=self.item_id).all()
            assert len(history) == 1
            assert history[0].price == 100.0
            assert history[0].source == 'initial'

    def test_record_price_history_duplicate_ignored(self):
        """Test that duplicate price within 6 hours is ignored."""
        with self.app.app_context():
            record_price_history(self.item_id, 100.0)

            # Try recording same price immediately
            result = record_price_history(self.item_id, 100.0)

            assert result is False
            history = PriceHistory.query.filter_by(item_id=self.item_id).all()
            assert len(history) == 1

    def test_record_price_history_change_accepted(self):
        """Test that price change is recorded regardless of time."""
        with self.app.app_context():
            record_price_history(self.item_id, 100.0)

            # Update price
            result = record_price_history(self.item_id, 90.0)

            assert result is True
            history = PriceHistory.query.filter_by(
                item_id=self.item_id).order_by(
                PriceHistory.recorded_at.desc()).all()
            assert len(history) == 2
            assert history[0].price == 90.0

    def test_record_price_history_stale_update(self):
        """Test that same price is recorded if > 6 hours passed."""
        with self.app.app_context():
            # Create old record manually
            old_time = datetime.now(timezone.utc) - timedelta(hours=7)
            old_record = PriceHistory(
                item_id=self.item_id,
                price=100.0,
                recorded_at=old_time
            )
            self.db.session.add(old_record)
            self.db.session.commit()

            # Record same price now
            result = record_price_history(self.item_id, 100.0)

            assert result is True
            history = PriceHistory.query.filter_by(item_id=self.item_id).all()
            assert len(history) == 2

    def test_get_price_history_stats(self):
        """Test statistics calculation."""
        with self.app.app_context():
            # Add 3 records: 100, 80, 120
            record_price_history(self.item_id, 100.0)
            record_price_history(self.item_id, 80.0)
            record_price_history(self.item_id, 120.0)

            stats = get_price_history_stats(self.item_id, days=7)

            assert stats['min'] == 80.0
            assert stats['max'] == 120.0
            assert stats['avg'] == 100.0

    def test_api_endpoint(self, client):
        """Test the API endpoint returns correct structure."""
        # Add history within app context
        with self.app.app_context():
            record_price_history(self.item_id, 50.0)

        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(self.user_id)

        response = client.get(f'/api/items/{self.item_id}/price-history')

        assert response.status_code == 200
        data = response.get_json()
        assert data['item_id'] == self.item_id
        assert len(data['history']) == 1
        assert data['history'][0]['price'] == 50.0
        assert 'min' in data['stats']

    def test_record_price_history_invalid_price_none(self):
        """Test that None price is rejected."""
        with self.app.app_context():
            result = record_price_history(self.item_id, None)
            assert result is False

            # No history should be added
            history = PriceHistory.query.filter_by(item_id=self.item_id).all()
            assert len(history) == 0

    def test_record_price_history_invalid_price_negative(self):
        """Test that negative price is rejected."""
        with self.app.app_context():
            result = record_price_history(self.item_id, -10.0)
            assert result is False

            # No history should be added
            history = PriceHistory.query.filter_by(item_id=self.item_id).all()
            assert len(history) == 0

    def test_get_price_history_stats_no_data(self):
        """Test stats returns None when no history exists."""
        with self.app.app_context():
            stats = get_price_history_stats(self.item_id, days=7)
            assert stats is None

    def test_get_price_history_stats_nonexistent_item(self):
        """Test stats returns None for nonexistent item."""
        with self.app.app_context():
            stats = get_price_history_stats(99999, days=7)
            assert stats is None
