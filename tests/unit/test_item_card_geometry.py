"""Layout-stability tests for the full item card across claim states.

Claim/unclaim replace the card in place via HTMX (GIV-CLM-010). The swap
must not change the card's height: the claim-attribution line is reserved
in every status and the action area keeps a single-row, minimum-height
footprint in every state, so the items grid does not reflow.

# @spec GIV-CLM-020
"""
import datetime
import re
from pathlib import Path

import pytest
from models import db, User, Item

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_CSS = REPO_ROOT / "static" / "css" / "main.css"


def _name_for_email(client, email):
    """Resolve a fixture user's name by email (web login is name-only)."""
    with client.application.app_context():
        user = User.query.filter_by(email=email).first()
        return user.name


def login_via_post(client, email):
    return client.post("/login", data={"name": _name_for_email(client, email)},
                       follow_redirects=True)


@pytest.fixture
def card_setup(app):
    """Owner Alice, claimer Bob, bystander Carol, and one priced item."""
    with app.app_context():
        owner = User(name="Alice", email="alice@example.com")
        claimer = User(name="Bob", email="bob@example.com")
        bystander = User(name="Carol", email="carol@example.com")
        db.session.add_all([owner, claimer, bystander])
        db.session.commit()

        item = Item(
            description="Geometry Test Item",
            user_id=owner.id,
            status="Available",
            price=39.99,
            price_updated_at=datetime.datetime(2026, 10, 29, 12, 0, 0),
        )
        db.session.add(item)
        db.session.commit()

        return owner.id, claimer.id, bystander.id, item.id


def _card_slice(html, item_id):
    """Extract one rendered card (its grid-column wrapper) from a page."""
    marker = f'id="item-card-{item_id}"'
    id_at = html.index(marker)
    start = html.rfind('<div class="col-md-6', 0, id_at)
    assert start != -1, "card column wrapper not found"
    nxt = html.find('id="item-card-', id_at + len(marker))
    return html[start:nxt if nxt != -1 else len(html)]


def _actions_slice(card_html):
    """Extract the card's action area (wrapper through the comments block)."""
    start = card_html.index("item-card-actions")
    end = card_html.find("<!-- Comments Section", start)
    return card_html[start:end if end != -1 else len(card_html)]


def test_available_card_reserves_attribution_line_and_action_area(client, card_setup):
    # @spec GIV-CLM-020
    _owner_id, _claimer_id, _bystander_id, item_id = card_setup
    login_via_post(client, "bob@example.com")

    card = _card_slice(client.get("/items").get_data(as_text=True), item_id)

    # The attribution line exists before any claim (empty reservation),
    # rendered as a single non-wrapping line.
    match = re.search(r'<p[^>]*item-claim-attribution[^>]*>', card)
    assert match, "attribution line must render in the Available state"
    assert "text-truncate" in match.group(0)
    assert "Claimed by" not in card
    assert "item-card-actions" in card


def test_claimed_card_keeps_single_row_action_area(client, card_setup):
    # @spec GIV-CLM-020
    _owner_id, _claimer_id, _bystander_id, item_id = card_setup
    login_via_post(client, "bob@example.com")

    response = client.post(f"/claim_item/{item_id}", headers={"HX-Request": "true"})
    assert response.status_code == 200
    card = response.get_data(as_text=True)

    assert "item-claim-attribution" in card
    assert "Claimed by Bob" in card
    assert "item-card-actions" in card
    actions = _actions_slice(card)
    # Claimed-by-me controls stay on one row like the Available state;
    # the old stacked flex-column block changed the card's height.
    assert "flex-column" not in actions
    assert "Unclaim" in actions
    assert "Update Status" in actions


def test_card_structure_for_other_viewer_after_claim(client, app, card_setup):
    # @spec GIV-CLM-020
    _owner_id, _claimer_id, _bystander_id, item_id = card_setup
    login_via_post(client, "bob@example.com")
    client.post(f"/claim_item/{item_id}", headers={"HX-Request": "true"})

    bystander_client = app.test_client()
    login_via_post(bystander_client, "carol@example.com")
    card = _card_slice(
        bystander_client.get("/items").get_data(as_text=True), item_id)

    assert "item-claim-attribution" in card
    assert "Claimed by Bob" in card
    assert "item-card-actions" in card


def test_own_item_card_uses_same_action_area(client, card_setup):
    # @spec GIV-CLM-020
    _owner_id, _claimer_id, _bystander_id, item_id = card_setup
    login_via_post(client, "alice@example.com")

    card = _card_slice(client.get("/items").get_data(as_text=True), item_id)

    assert "item-card-actions" in card


def test_price_line_cannot_wrap(client, card_setup):
    # @spec GIV-CLM-020
    _owner_id, _claimer_id, _bystander_id, item_id = card_setup
    login_via_post(client, "bob@example.com")

    card = _card_slice(client.get("/items").get_data(as_text=True), item_id)

    assert "flex-nowrap" in card, "price row must not wrap to a second line"
    assert "text-nowrap" in card, "the 'as of' date must stay on the price line"


def test_action_area_min_height_rule_in_css():
    # @spec GIV-CLM-020
    css = MAIN_CSS.read_text()
    assert re.search(r"\.item-card-actions\s*\{[^}]*min-height\s*:", css), (
        "static/css/main.css must floor the action area height via "
        ".item-card-actions { min-height: ... }"
    )


def test_action_group_wraps_state_controls_in_available_and_claimed(client, card_setup):
    # @spec GIV-CLM-020
    _owner_id, _claimer_id, _bystander_id, item_id = card_setup
    login_via_post(client, "bob@example.com")

    card = _card_slice(client.get("/items").get_data(as_text=True), item_id)
    assert "item-card-action-group" in _actions_slice(card), (
        "Available controls must sit in the non-wrapping action group"
    )

    response = client.post(f"/claim_item/{item_id}", headers={"HX-Request": "true"})
    assert response.status_code == 200
    claimed_actions = _actions_slice(response.get_data(as_text=True))
    assert "item-card-action-group" in claimed_actions, (
        "Claimed-by-me controls must sit in the same action group"
    )


def test_action_group_wraps_state_controls_in_splitting_state(client, app, card_setup):
    # @spec GIV-CLM-020
    _owner_id, _claimer_id, _bystander_id, item_id = card_setup
    with app.app_context():
        item = db.session.get(Item, item_id)
        item.status = "Splitting"
        db.session.commit()

    login_via_post(client, "bob@example.com")
    card = _card_slice(client.get("/items").get_data(as_text=True), item_id)

    actions = _actions_slice(card)
    assert "Join Split" in actions
    assert "item-card-action-group" in actions, (
        "Splitting controls must sit in the same action group"
    )


def test_claimed_by_other_badge_cannot_wrap(client, app, card_setup):
    # @spec GIV-CLM-020
    _owner_id, _claimer_id, _bystander_id, item_id = card_setup
    login_via_post(client, "bob@example.com")
    client.post(f"/claim_item/{item_id}", headers={"HX-Request": "true"})

    bystander_client = app.test_client()
    login_via_post(bystander_client, "carol@example.com")
    card = _card_slice(
        bystander_client.get("/items").get_data(as_text=True), item_id)

    actions = _actions_slice(card)
    assert "text-nowrap" in actions, (
        "the claimed-by-another status badge must not wrap to a second line"
    )


def test_action_group_css_guarantees_one_line_at_any_width():
    # @spec GIV-CLM-020
    css = MAIN_CSS.read_text()

    row = re.search(r"\.item-card-actions\s*\{([^}]*)\}", css)
    assert row, ".item-card-actions rule missing"
    assert re.search(r"flex-wrap\s*:\s*nowrap", row.group(1)), (
        "the action row itself must never wrap its groups"
    )

    slot = re.search(r"\.item-card-action-group\s+\.btn\s*\{([^}]*)\}", css)
    assert slot, ".item-card-action-group .btn rule missing"
    body = slot.group(1)
    assert re.search(r"flex\s*:\s*1\s", body), (
        "each state control must take an equal flex slot"
    )
    assert re.search(r"white-space\s*:\s*nowrap", body), (
        "control labels must not wrap to a second line"
    )
    assert re.search(r"min-width\s*:\s*0", body), (
        "slots must be allowed to shrink so labels truncate instead"
    )
