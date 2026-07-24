"""Shared claim/unclaim/purchase logic used by the web and API blueprints.

Rules mirror the pre-existing web behavior; `purchase_item` additionally
rejects purchasing an item claimed by a different user (the web edit form
was more permissive, but the API is the stricter, safer surface).
"""

from models import db


class ItemActionError(Exception):
    """An action was rejected; `code` is machine-readable, `message` human-readable."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def claim_item(item, user_id):
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
    if item.user_id == user_id:
        raise ItemActionError('own_item', 'You cannot purchase your own item.')
    if item.status == 'Purchased':
        raise ItemActionError('already_purchased', 'This item is already purchased.')
    if item.status == 'Claimed' and item.last_updated_by_id != user_id:
        raise ItemActionError('claimed_by_other', 'This item is claimed by someone else.')
    item.status = 'Purchased'
    item.last_updated_by_id = user_id
    db.session.commit()
