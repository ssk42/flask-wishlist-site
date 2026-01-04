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
