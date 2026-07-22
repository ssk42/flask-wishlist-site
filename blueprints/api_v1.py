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
from config import PRIORITY_CHOICES
from services import item_service
from services.form_validators import FormValidator, validate_item_fields
from services.item_service import ItemActionError

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


def _get_item_or_none(item_id):
    return db.session.get(Item, item_id)


def _stringified(data):
    """JSON payloads carry numbers; FormValidator expects form-style strings."""
    return {k: ('' if v is None else str(v)) for k, v in data.items()}


def _validated_item_fields(data):
    """Run the shared web validations over a JSON payload.

    Returns (fields_dict, errors_list); exactly one is meaningful.
    """
    validator = FormValidator(_stringified(data))
    description = validator.required('description', 'A description is required.')
    link = validator.optional('link')
    image_url = validator.optional('image_url')
    category = validator.optional('category')
    priority = validator.choice('priority', PRIORITY_CHOICES, default=PRIORITY_CHOICES[0])
    event_id = validator.parse_int('event_id')
    price = validator.parse_float('price', 'Price must be a valid number.')
    size = validator.optional('size', max_length=50)
    color = validator.optional('color', max_length=50)
    quantity = validator.parse_int('quantity', 'Quantity must be a valid number.',
                                   min_value=1, max_value=99,
                                   range_error='Quantity must be between 1 and 99.')
    validate_item_fields(validator, description, link, image_url, price, event_id)
    if not validator.is_valid():
        return None, validator.errors
    return {
        'description': description, 'link': link, 'image_url': image_url,
        'category': category, 'priority': priority, 'event_id': event_id,
        'price': price, 'size': size, 'color': color, 'quantity': quantity,
    }, None


@bp.route('/items', methods=['POST'])
def create_item():
    data = request.get_json(silent=True) or {}
    fields, errors = _validated_item_fields(data)
    if errors:
        return jsonify({'errors': errors}), 400

    item = Item(user_id=current_user.id, status='Available', **fields)
    db.session.add(item)
    db.session.commit()
    current_app.logger.info(f'API item created by user_id={current_user.id}: {item.description[:50]}')
    return jsonify({'item': serialize_item(item, current_user)}), 201


@bp.route('/items/<int:item_id>', methods=['PATCH'])
def update_item(item_id):
    item = _get_item_or_none(item_id)
    if item is None:
        return _json_error(404, 'not_found')
    if item.user_id != current_user.id:
        return _json_error(403, 'forbidden')

    # Merge current values with the patch so partial updates validate correctly.
    merged = {
        'description': item.description, 'link': item.link, 'image_url': item.image_url,
        'category': item.category, 'priority': item.priority, 'event_id': item.event_id,
        'price': item.price, 'size': item.size, 'color': item.color,
        'quantity': item.quantity,
    }
    patch = request.get_json(silent=True) or {}
    merged.update(patch)
    fields, errors = _validated_item_fields(merged)
    if errors:
        return jsonify({'errors': errors}), 400

    # Only persist fields the patch actually sent. Validation ran over the full
    # merged dict for context, but choice()/optional() coercion can rewrite
    # fields the patch never touched (e.g. a stored priority of None becomes the
    # default), which would silently lose the item's real value.
    for key, value in fields.items():
        if key in patch:
            setattr(item, key, value)
    db.session.commit()
    return jsonify({'item': serialize_item(item, current_user)})


@bp.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    item = _get_item_or_none(item_id)
    if item is None:
        return _json_error(404, 'not_found')
    if item.user_id != current_user.id:
        return _json_error(403, 'forbidden')
    db.session.delete(item)
    db.session.commit()
    return jsonify({'ok': True})


def _item_action(item_id, action):
    item = _get_item_or_none(item_id)
    if item is None:
        return _json_error(404, 'not_found')
    try:
        action(item, current_user.id)
    except ItemActionError as err:
        return _json_error(409, err.code, err.message)
    return jsonify({'item': serialize_item(item, current_user)})


@bp.route('/items/<int:item_id>/claim', methods=['POST'])
def claim_item(item_id):
    return _item_action(item_id, item_service.claim_item)


@bp.route('/items/<int:item_id>/unclaim', methods=['POST'])
def unclaim_item(item_id):
    return _item_action(item_id, item_service.unclaim_item)


@bp.route('/items/<int:item_id>/purchase', methods=['POST'])
def purchase_item(item_id):
    return _item_action(item_id, item_service.purchase_item)
