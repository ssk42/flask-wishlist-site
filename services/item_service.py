"""Shared claim/unclaim/purchase logic used by the web and API blueprints.

Rules mirror the pre-existing web behavior; `purchase_item` additionally
rejects purchasing an item claimed by a different user (the web edit form
was more permissive, but the API is the stricter, safer surface).
"""

import datetime

from dateutil.relativedelta import relativedelta

from models import db, Item


class ItemActionError(Exception):
    """An action was rejected; `code` is machine-readable, `message` human-readable."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def claim_item(item, user_id):
    # ORDER IS LOAD-BEARING: own_item must be checked BEFORE availability.
    # Siri speaks these messages aloud (ClaimItemIntent). If the availability
    # check ran first, an owner asking to claim their own gift would hear
    # "no longer available to claim" — telling them someone claimed it, which
    # is exactly what surprise protection exists to hide. Pinned by
    # test_claim_own_item_reports_own_item_even_when_claimed.
    # @spec GIV-CLM-001, GIV-CLM-002, GIV-CLM-003, GIV-CLM-004
    if item.user_id == user_id:
        raise ItemActionError('own_item', 'You cannot claim your own item.')
    if item.status != 'Available':
        raise ItemActionError('not_available', 'This item is no longer available to claim.')
    item.status = 'Claimed'
    item.last_updated_by_id = user_id
    db.session.commit()


def unclaim_item(item, user_id):
    if item.status != 'Claimed' or item.last_updated_by_id != user_id:
        raise ItemActionError('not_claimer', 'You cannot unclaim this item.')
    item.status = 'Available'
    item.last_updated_by_id = user_id
    db.session.commit()


def purchase_item(item, user_id):
    # Same ordering requirement as claim_item above, for the same reason.
    if item.user_id == user_id:
        raise ItemActionError('own_item', 'You cannot purchase your own item.')
    if item.status == 'Purchased':
        raise ItemActionError('already_purchased', 'This item is already purchased.')
    if item.status == 'Claimed' and item.last_updated_by_id != user_id:
        raise ItemActionError('claimed_by_other', 'This item is claimed by someone else.')
    item.status = 'Purchased'
    item.last_updated_by_id = user_id
    db.session.commit()


def archive_stale_items(now=None):
    # @spec OWN-ITEM-019, OWN-ITEM-020
    """Archive items requested more than 10 months ago.

    An item is stale when it is not already archived and its `created_at`
    is more than 10 months before `now`. Items tied to an event dated
    today or later are exempt — they are still in play. Archiving only
    sets `archived_at`, so status, claims, contributions, and comments
    survive and the owner can restore the item from the Archived view.

    Each affected owner receives a single summary notification. Returns
    {'archived_count': int, 'owner_count': int}.
    """
    from services.notification_service import create_notification

    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - relativedelta(months=10)
    today = now.date()

    candidates = (
        Item.query
        .filter(Item.archived_at.is_(None), Item.created_at < cutoff)
        .order_by(Item.user_id)
        .all()
    )

    by_owner = {}
    for item in candidates:
        if item.event_id is not None and item.event is not None and item.event.date >= today:
            continue
        item.archived_at = now
        by_owner[item.user_id] = by_owner.get(item.user_id, 0) + 1

    if by_owner:
        db.session.commit()
        for owner_id, count in by_owner.items():
            noun = 'gift' if count == 1 else 'gifts'
            verb = 'was' if count == 1 else 'were'
            create_notification(
                owner_id,
                f'{count} of your requested {noun} {verb} archived automatically '
                '(requested over 10 months ago). You can restore them from your Archived view.',
                '/items?status=Archived',
            )

    return {'archived_count': sum(by_owner.values()), 'owner_count': len(by_owner)}
