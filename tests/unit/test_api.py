"""Tests for API endpoints."""
import pytest
from unittest.mock import patch, MagicMock
import datetime


class TestExtractionHealth:
    """Tests for /api/health/extraction endpoint."""

    def test_extraction_health_empty(self, client, login):
        """Should return empty stats when no extraction logs exist."""
        response = client.get('/api/health/extraction')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['period'] == '24h'
        assert data['stats'] == []

    def test_extraction_health_with_logs(self, app, client, login):
        """Should return stats grouped by domain."""
        from models import db, PriceExtractionLog
        
        with app.app_context():
            # Add some extraction logs
            log1 = PriceExtractionLog(
                domain='amazon.com',
                url='https://amazon.com/product1',
                success=True,
                price=29.99,
                extraction_method='meta'
            )
            log2 = PriceExtractionLog(
                domain='amazon.com',
                url='https://amazon.com/product2',
                success=False,
                error_type='captcha'
            )
            log3 = PriceExtractionLog(
                domain='target.com',
                url='https://target.com/product1',
                success=True,
                price=19.99
            )
            db.session.add_all([log1, log2, log3])
            db.session.commit()

        response = client.get('/api/health/extraction')
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['status'] == 'ok'
        assert len(data['stats']) == 2
        
        # Find amazon stats
        amazon_stats = next((s for s in data['stats'] if s['domain'] == 'amazon.com'), None)
        assert amazon_stats is not None
        assert amazon_stats['total'] == 2
        assert amazon_stats['success'] == 1
        assert amazon_stats['rate'] == 50.0


class TestPriceHistoryAPI:
    """Tests for /api/items/<id>/price-history endpoint."""
    
    def test_price_history_not_found(self, client, login):
        """Should return 404 for non-existent item."""
        response = client.get('/api/items/99999/price-history')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_price_history_empty(self, app, client, login, user):
        """Should return empty history for item with no price history."""
        from models import db, Item
        
        with app.app_context():
            # user fixture returns user ID, not User object
            item = Item(description="No History Item", user_id=user, price=25.00)
            db.session.add(item)
            db.session.commit()
            item_id = item.id
        
        response = client.get(f'/api/items/{item_id}/price-history')
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['item_id'] == item_id
        assert data['current_price'] == 25.00
        assert data['history'] == []

    def test_price_history_with_data(self, app, client, login, user):
        """Should return price history with stats."""
        from models import db, Item, PriceHistory
        
        with app.app_context():
            # user fixture returns user ID, not User object
            item = Item(description="Price History Item", user_id=user, price=25.00)
            db.session.add(item)
            db.session.commit()
            
            # Add price history
            h1 = PriceHistory(item_id=item.id, price=30.00, source='initial')
            h2 = PriceHistory(item_id=item.id, price=25.00, source='auto')
            db.session.add_all([h1, h2])
            db.session.commit()
            item_id = item.id
        
        response = client.get(f'/api/items/{item_id}/price-history')
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['item_id'] == item_id
        assert len(data['history']) == 2
        assert data['stats'] is not None
        assert data['stats']['min'] == 25.00
        assert data['stats']['max'] == 30.00
