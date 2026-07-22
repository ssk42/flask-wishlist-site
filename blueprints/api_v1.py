"""JSON API v1 for native clients (iOS app).

Auth: 'Authorization: Bearer <token>' resolved by the app-level
request_loader. The before_request gate below rejects everything
unauthenticated except login. CSRF is exempted at registration time
in app.py (token auth replaces it).
"""

import hmac

from flask import Blueprint, current_app, g, jsonify, request
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from extensions import limiter
from models import Item, User, db
from services.api_auth import issue_token, revoke_token
from services.api_serializers import serialize_item, serialize_user

bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

PUBLIC_ENDPOINTS = {'api_v1.login'}


def _json_error(status, code, message=None):
    payload = {'error': code}
    if message:
        payload['message'] = message
    return jsonify(payload), status


@bp.before_request
def require_token_auth():
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    # A security gate must reflect THIS request's credentials, never a
    # current_user cached earlier in the same app context. In production each
    # request gets its own app context, so this pop is a no-op; it only matters
    # under the test harness (one shared app context per test), where it forces
    # re-resolution via the request_loader so a just-revoked token is rejected.
    g.pop('_login_user', None)
    if not current_user.is_authenticated:
        return _json_error(401, 'unauthorized')
    return None


@bp.route('/auth/login', methods=['POST'])
@limiter.limit('5 per minute')
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    supplied_code = data.get('family_code') or ''
    family_code = current_app.config.get('FAMILY_PASSWORD') or ''

    if not hmac.compare_digest(supplied_code.encode(), family_code.encode()):
        return _json_error(401, 'invalid_family_code')

    user = User.query.filter_by(email=email).first()
    if user is None:
        current_app.logger.warning(f'API login failed for email: {email}')
        return _json_error(401, 'unknown_email')

    current_app.logger.info(f'API login: {email} (user_id={user.id})')
    return jsonify({'token': issue_token(user.id), 'user': serialize_user(user)})


@bp.route('/auth/logout', methods=['POST'])
def logout():
    auth_header = request.headers.get('Authorization', '')
    revoke_token(auth_header[len('Bearer '):] if auth_header.startswith('Bearer ') else None)
    return jsonify({'ok': True})


@bp.route('/users', methods=['GET'])
def list_users():
    counts = dict(
        db.session.query(Item.user_id, func.count(Item.id)).group_by(Item.user_id).all()
    )
    users = User.query.order_by(User.name).all()
    return jsonify({'users': [serialize_user(u, item_count=counts.get(u.id, 0)) for u in users]})


@bp.route('/items', methods=['GET'])
def list_items():
    query = Item.query.options(joinedload(Item.last_updated_by))

    user_id = request.args.get('user_id', type=int)
    status = request.args.get('status')
    category = request.args.get('category')
    q = request.args.get('q')

    if user_id:
        query = query.filter(Item.user_id == user_id)
    if status:
        # Surprise protection: a status filter must never reveal the status
        # of the viewer's own items by their inclusion in the result set.
        query = query.filter(Item.status == status, Item.user_id != current_user.id)
    if category:
        query = query.filter(Item.category == category)
    if q:
        query = query.filter(Item.description.ilike(f'%{q}%'))

    items = query.order_by(Item.created_at.desc(), Item.id.desc()).all()
    return jsonify({'items': [serialize_item(i, current_user) for i in items]})


@bp.route('/my-claims', methods=['GET'])
def my_claims():
    items = (
        Item.query.options(joinedload(Item.user), joinedload(Item.last_updated_by))
        .filter(
            Item.last_updated_by_id == current_user.id,
            Item.status.in_(['Claimed', 'Purchased']),
            Item.user_id != current_user.id,
        )
        .order_by(Item.user_id, Item.description)
        .all()
    )
    return jsonify({'items': [serialize_item(i, current_user) for i in items]})
