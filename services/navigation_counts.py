"""Lazy navigation summaries, shared only within the current request."""

from flask import has_request_context, request
from flask_login import current_user
from sqlalchemy import event, func
from sqlalchemy.orm import Session

from models import db, Item, Notification


def _values():
    # Use the request rather than g: an app context can span multiple requests.
    if not hasattr(request, '_navigation_counts'):
        request._navigation_counts = {}
    return request._navigation_counts


def _invalidate():
    if has_request_context():
        _values().clear()


@event.listens_for(Session, 'after_flush')
def _invalidate_after_flush(session, flush_context):
    # @spec GIV-CLM-015, VW-UI-011
    if any(isinstance(obj, (Item, Notification))
           for obj in session.new | session.dirty | session.deleted):
        _invalidate()


@event.listens_for(Session, 'after_soft_rollback')
def _invalidate_after_rollback(session, previous_transaction):
    # @spec GIV-CLM-015, VW-UI-011
    _invalidate()


@event.listens_for(Session, 'do_orm_execute')
def _invalidate_bulk_write(state):
    # @spec GIV-CLM-015, VW-UI-011
    # Bulk writes bypass normal per-instance flush tracking. Conservatively
    # discard both summaries, including entries for a previous recipient.
    if state.is_update or state.is_delete or state.is_insert:
        _invalidate()


def claim_summary():
    # @spec GIV-CLM-012, GIV-CLM-013, VW-UI-008, VW-UI-009
    """Return active claim/purchase counts for the authenticated viewer."""
    if not current_user.is_authenticated:
        return {'claimed_count': 0, 'purchased_count': 0}
    db.session.flush()
    key = ('claims', current_user.id)
    values = _values()
    if key not in values:
        counts = dict(db.session.query(Item.status, func.count(Item.id)).filter(
            Item.last_updated_by_id == current_user.id,
            Item.user_id != current_user.id,
            Item.archived_at.is_(None),
            Item.status.in_(['Claimed', 'Purchased']),
        ).group_by(Item.status).all())
        values[key] = {'claimed_count': counts.get('Claimed', 0),
                       'purchased_count': counts.get('Purchased', 0)}
    return values[key]


def seed_claim_summary(items):
    # @spec GIV-CLM-014
    """Seed from My Claims' complete unpaginated, current-viewer collection."""
    db.session.flush()
    summary = {'claimed_count': sum(i.status == 'Claimed' for i in items),
               'purchased_count': sum(i.status == 'Purchased' for i in items)}
    _values()[('claims', current_user.id)] = summary
    return summary


def unread_count():
    # @spec VW-UI-007, VW-UI-008, VW-UI-009
    """Count unread notifications only when a rendered sidebar needs them."""
    if not current_user.is_authenticated:
        return 0
    db.session.flush()
    key = ('unread', current_user.id)
    values = _values()
    if key not in values:
        values[key] = current_user.unread_count
    return values[key]


def seed_unread_count(notifications):
    # @spec VW-UI-010
    """Seed from the complete unpaginated notification list for this viewer."""
    db.session.flush()
    _values()[('unread', current_user.id)] = sum(not n.is_read for n in notifications)
