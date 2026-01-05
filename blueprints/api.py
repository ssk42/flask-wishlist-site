"""API blueprint for AJAX/fetch endpoints."""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/fetch-metadata', methods=['POST'])
@login_required
def fetch_metadata():
    """Fetch metadata from a URL for item auto-fill."""
    from services.price_service import fetch_metadata as fetch_meta

    if not request.json or 'url' not in request.json:
        return jsonify({'error': 'Missing URL'}), 400

    url = request.json['url']
    try:
        metadata = fetch_meta(url)
        return jsonify(metadata)
    except Exception as e:
        current_app.logger.error(f"Metadata fetch failed: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/health/extraction', methods=['GET'])
@login_required
def extraction_health():
    """Get price extraction health statistics for the last 24h."""
    from models import db, PriceExtractionLog
    from sqlalchemy import func, case
    import datetime

    try:
        # Last 24h stats
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
        
        stats = db.session.query(
            PriceExtractionLog.domain,
            func.count().label('total'),
            func.sum(case((PriceExtractionLog.success, 1), else_=0)).label('success')
        ).filter(
            PriceExtractionLog.created_at > cutoff
        ).group_by(PriceExtractionLog.domain).all()
        
        results = []
        for domain, total, success in stats:
            # Handle potential None from sum
            success_count = success if success else 0
            rate = (success_count / total) * 100 if total > 0 else 0
            results.append({
                'domain': domain,
                'total': total,
                'success': success_count,
                'rate': round(rate, 1)
            })
            
        return jsonify({
            'status': 'ok',
            'period': '24h',
            'stats': results
        })
    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return jsonify({'error': str(e)}), 500
@bp.route('/items/<int:item_id>/price-history', methods=['GET'])
@login_required
def get_item_price_history(item_id):
    """Get price history for an item."""
    from models import db, Item, PriceHistory
    from services.price_history import get_price_history_stats
    
    # Verify item exists (and optionally permissions, though read-only is low risk)
    item = db.session.get(Item, item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
        
    try:
        # Get raw history
        history = PriceHistory.query.filter_by(item_id=item_id)\
            .order_by(PriceHistory.recorded_at.asc())\
            .limit(90).all()  # Limit query size
            
        # Get processed stats
        stats = get_price_history_stats(item_id)
        
        return jsonify({
            'item_id': item_id,
            'current_price': item.price,
            'history': [
                {
                    'price': h.price, 
                    'date': h.recorded_at.isoformat(),
                    'source': h.source
                }
                for h in history
            ],
            'stats': stats
        })
    except Exception as e:
        current_app.logger.error(f"Price history fetch failed for {item_id}: {e}")
        return jsonify({'error': str(e)}), 500
