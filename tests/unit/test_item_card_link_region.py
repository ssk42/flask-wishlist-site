"""Clickable link-region tests for the item cards.

The image-and-content region of a card (everything above the actions
footer) opens the item's link in a new tab when the item has one, via a
stretched-link anchor scoped to a positioned wrapper around that region.
Controls inside the region keep their own clicks, and a card whose item
has no link renders no such target.

# @spec GIV-CLM-022
"""
import datetime
import re

import pytest
from models import db, User, Item


def _name_for_email(client, email):
    with client.application.app_context():
        user = User.query.filter_by(email=email).first()
        return user.name


def login_via_post(client, email):
    return client.post("/login", data={"name": _name_for_email(client, email)},
                       follow_redirects=True)


@pytest.fixture
def link_setup(app):
    """Owner Alice, viewer Bob, one linked priced item, one linkless item."""
    with app.app_context():
        owner = User(name="Alice", email="alice@example.com")
        viewer = User(name="Bob", email="bob@example.com")
        db.session.add_all([owner, viewer])
        db.session.commit()

        linked = Item(
            description="Linked Item",
            user_id=owner.id,
            status="Available",
            link="https://example.com/some-gift",
            price=25.00,
            price_updated_at=datetime.datetime(2026, 11, 1, 12, 0, 0),
        )
        linkless = Item(
            description="Linkless Item",
            user_id=owner.id,
            status="Available",
        )
        db.session.add_all([linked, linkless])
        db.session.commit()

        return owner.id, viewer.id, linked.id, linkless.id


def _card_slice(html, item_id):
    marker = f'id="item-card-{item_id}"'
    id_at = html.index(marker)
    start = html.rfind('<div class="col-md-6', 0, id_at)
    assert start != -1, "card column wrapper not found"
    nxt = html.find('id="item-card-', id_at + len(marker))
    return html[start:nxt if nxt != -1 else len(html)]


def _dashboard_slice(html, item_id):
    marker = f'id="dashboard-item-{item_id}"'
    id_at = html.index(marker)
    start = html.rfind('<div class="glass-card', 0, id_at)
    assert start != -1, "dashboard card not found"
    nxt = html.find('id="dashboard-item-', id_at + len(marker))
    return html[start:nxt if nxt != -1 else len(html)]


def test_full_card_region_is_clickable_link(client, link_setup):
    # @spec GIV-CLM-022
    _owner_id, _viewer_id, linked_id, _linkless_id = link_setup
    login_via_post(client, "bob@example.com")

    card = _card_slice(client.get("/items").get_data(as_text=True), linked_id)

    match = re.search(r'<a[^>]*stretched-link[^>]*>', card)
    assert match, "linked card must render a stretched-link anchor"
    assert 'href="https://example.com/some-gift"' in match.group(0)
    assert 'target="_blank"' in match.group(0)
    # The click target lives in the region above the actions footer.
    assert card.index("stretched-link") < card.index("item-card-actions")
    # Its reach is scoped by a positioned wrapper around the region.
    assert "position-relative" in card[:card.index("stretched-link")]


def test_full_card_without_link_has_no_click_target(client, link_setup):
    # @spec GIV-CLM-022
    _owner_id, _viewer_id, _linked_id, linkless_id = link_setup
    login_via_post(client, "bob@example.com")

    card = _card_slice(client.get("/items").get_data(as_text=True), linkless_id)

    assert "stretched-link" not in card


def test_price_refresh_control_stays_above_link_overlay(client, link_setup):
    # @spec GIV-CLM-022
    _owner_id, _viewer_id, linked_id, _linkless_id = link_setup
    login_via_post(client, "bob@example.com")

    card = _card_slice(client.get("/items").get_data(as_text=True), linked_id)

    match = re.search(r'<form[^>]*refresh-price[^>]*>', card)
    assert match, "priced linked item must render the refresh-price form"
    assert "position-relative" in match.group(0), (
        "the refresh control must be positioned above the stretched link"
    )
    assert "z-2" in match.group(0)


def test_dashboard_card_region_is_clickable_link(client, link_setup):
    # @spec GIV-CLM-022
    _owner_id, _viewer_id, linked_id, linkless_id = link_setup
    login_via_post(client, "bob@example.com")

    page = client.get("/").get_data(as_text=True)

    card = _dashboard_slice(page, linked_id)
    match = re.search(r'<a[^>]*stretched-link[^>]*>', card)
    assert match, "linked dashboard card must render a stretched-link anchor"
    assert 'href="https://example.com/some-gift"' in match.group(0)

    linkless_card = _dashboard_slice(page, linkless_id)
    assert "stretched-link" not in linkless_card
