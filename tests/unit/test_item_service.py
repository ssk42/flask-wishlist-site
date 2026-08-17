"""Tests for the shared claim/unclaim/purchase service."""

import pytest

from models import db, Item
from services import item_service
from services.item_service import ItemActionError


def _item(owner_id, status="Available", last_updated_by_id=None):
    item = Item(description="Thing", user_id=owner_id, status=status,
                last_updated_by_id=last_updated_by_id)
    db.session.add(item)
    db.session.commit()
    return item


def test_claim_success(app, user, other_user):
    # @spec GIV-CLM-003
    with app.app_context():
        item = _item(owner_id=user)
        item_service.claim_item(item, other_user)
        assert item.status == "Claimed"
        assert item.last_updated_by_id == other_user


def test_cannot_claim_own_item(app, user):
    # @spec GIV-CLM-002
    with app.app_context():
        item = _item(owner_id=user)
        with pytest.raises(ItemActionError) as exc:
            item_service.claim_item(item, user)
        assert exc.value.code == "own_item"
        assert item.status == "Available"


def test_cannot_claim_unavailable_item(app, user, other_user):
    # @spec GIV-CLM-004
    with app.app_context():
        item = _item(owner_id=user, status="Claimed", last_updated_by_id=other_user)
        with pytest.raises(ItemActionError) as exc:
            item_service.claim_item(item, other_user)
        assert exc.value.code == "not_available"


def test_unclaim_by_claimer(app, user, other_user):
    # @spec GIV-CLM-005
    with app.app_context():
        item = _item(owner_id=user, status="Claimed", last_updated_by_id=other_user)
        item_service.unclaim_item(item, other_user)
        assert item.status == "Available"


def test_unclaim_rejected_for_non_claimer(app, user, other_user):
    # @spec GIV-CLM-006
    with app.app_context():
        item = _item(owner_id=other_user, status="Claimed", last_updated_by_id=user)
        with pytest.raises(ItemActionError) as exc:
            item_service.unclaim_item(item, other_user)
        assert exc.value.code == "not_claimer"


def test_purchase_available_item(app, user, other_user):
    with app.app_context():
        item = _item(owner_id=user)
        item_service.purchase_item(item, other_user)
        assert item.status == "Purchased"
        assert item.last_updated_by_id == other_user


def test_purchase_own_claim(app, user, other_user):
    with app.app_context():
        item = _item(owner_id=user, status="Claimed", last_updated_by_id=other_user)
        item_service.purchase_item(item, other_user)
        assert item.status == "Purchased"


def test_cannot_purchase_item_claimed_by_someone_else(app, user, other_user):
    with app.app_context():
        item = _item(owner_id=other_user, status="Claimed", last_updated_by_id=user)
        # a third party is simulated by other_user being the owner; use a fresh user
        from models import User
        third = User(name="Third", email="third@example.com")
        db.session.add(third)
        db.session.commit()
        with pytest.raises(ItemActionError) as exc:
            item_service.purchase_item(item, third.id)
        assert exc.value.code == "claimed_by_other"


def test_cannot_purchase_own_item(app, user):
    with app.app_context():
        item = _item(owner_id=user)
        with pytest.raises(ItemActionError) as exc:
            item_service.purchase_item(item, user)
        assert exc.value.code == "own_item"


def test_claim_own_item_reports_own_item_even_when_claimed(app, user, other_user):
    """Owners must never learn their own gift was claimed — not even via the error.

    Siri speaks these messages aloud, so the guard order in claim_item is a
    surprise-protection boundary, not a style choice. If availability were
    checked before ownership, an owner asking to claim their own already-claimed
    gift would hear "no longer available to claim" and know someone took it.
    """
    with app.app_context():
        item = _item(owner_id=user, status="Claimed", last_updated_by_id=other_user)
        with pytest.raises(ItemActionError) as exc:
            item_service.claim_item(item, user)
        assert exc.value.code == "own_item"
        assert "available" not in exc.value.message.lower()


def test_purchase_own_item_reports_own_item_even_when_purchased(app, user, other_user):
    """Same boundary as claiming: ownership is checked before purchase state."""
    with app.app_context():
        item = _item(owner_id=user, status="Purchased", last_updated_by_id=other_user)
        with pytest.raises(ItemActionError) as exc:
            item_service.purchase_item(item, user)
        assert exc.value.code == "own_item"
        assert "purchased" not in exc.value.message.lower()
