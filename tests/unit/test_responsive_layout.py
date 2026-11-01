"""Responsive-layout tests: pages must fit the viewport at any width.

A flex item's automatic minimum size is its content's min-content width,
and min-content propagates through every flex ancestor in turn. The item
card is a flex column and its title is nowrap (text-truncate), so a long
title's min-content (measured at 570px for a real catalogue title)
propagated through the card body and the grid column and expanded the
items page's layout viewport to 668px on a 390px phone; a wide product
photo's intrinsic width (894px) propagated the same way through the grid
column and the shell's main content and laid the page out 992px wide at a
606px window. The stylesheet breaks that chain at every flex item on the
path — shell main content, grid columns, and card flex children may all
shrink below min-content — so truncation ellipsizes the title and the
cover frame crops the photo instead of either stretching the page. The
same file carries the small-viewport rules for image containment,
safe-area clearance under the floating action button and tab bar, and
44px card action tap targets.

# @spec VW-RSP-001, VW-RSP-002, VW-RSP-003, VW-RSP-004, VW-RSP-005
"""
import re
from pathlib import Path

import pytest
from models import db, User, Item

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_CSS = REPO_ROOT / "static" / "css" / "main.css"
BASE_HTML = REPO_ROOT / "templates" / "base.html"

LONG_TITLE = (
    "KitchenAid Classic Series 4.5 Quart Tilt-Head Stand Mixer "
    "K45SS, Onyx Black with Stainless Steel Bowl and Attachments"
)


def _css():
    return MAIN_CSS.read_text()


def _rule(css, selector_pattern):
    """Return the declaration block of the first matching rule, or ''."""
    match = re.search(selector_pattern + r"\s*\{([^}]*)\}", css)
    return match.group(1) if match else ""


def test_base_template_declares_device_viewport():
    """@spec VW-RSP-001: pages opt into the device-width layout viewport."""
    assert 'name="viewport" content="width=device-width, initial-scale=1"' \
        in BASE_HTML.read_text()


def test_card_flex_children_may_shrink_below_min_content():
    """@spec VW-RSP-001, VW-RSP-002: the min-content chain is broken."""
    css = _css()
    card_children = _rule(css, r"\.glass-card\s*>\s*\*")
    assert "min-width: 0" in card_children
    flex_row_children = _rule(css, r"\.glass-card\s+\.d-flex\s*>\s*\*")
    assert "min-width: 0" in flex_row_children


def test_shell_main_content_may_shrink_below_min_content():
    """@spec VW-RSP-001: the flex shell cannot be widened by its content.

    The main content region is the growing flex item of the sidebar
    shell; with an automatic minimum size, any min-content that reaches
    it — a wide image through its grid column — widens the whole page.
    """
    css = _css()
    main_content = _rule(css, r"\.main-content")
    assert "min-width: 0" in main_content


def test_grid_columns_may_shrink_below_min_content():
    """@spec VW-RSP-001, VW-RSP-003: columns size from their classes.

    A grid column is a non-shrinking flex item of its row; with an
    automatic minimum size it passes a wide image's intrinsic width up
    the chain instead of holding the width its column classes assign.
    """
    css = _css()
    columns = _rule(css, r"\.row\s*>\s*\*")
    assert "min-width: 0" in columns


@pytest.fixture
def long_title_setup(app):
    """An owner with one item whose title is far wider than a phone card."""
    with app.app_context():
        owner = User(name="Alice", email="alice@example.com")
        viewer = User(name="Bob", email="bob@example.com")
        db.session.add_all([owner, viewer])
        db.session.commit()
        item = Item(
            description=LONG_TITLE,
            user_id=owner.id,
            status="Available",
            price=399.99,
        )
        db.session.add(item)
        db.session.commit()
        return owner.id, viewer.id, item.id


def _name_for_email(client, email):
    with client.application.app_context():
        return User.query.filter_by(email=email).first().name


def test_long_title_still_renders_truncating_title(client, long_title_setup):
    """@spec VW-RSP-002: the card keeps its truncating title element."""
    _, _, item_id = long_title_setup
    client.post("/login", data={"name": _name_for_email(client, "bob@example.com")},
                follow_redirects=True)
    html = client.get("/items").get_data(as_text=True)
    marker = f'id="item-card-{item_id}"'
    assert marker in html
    card_html = html[html.index(marker):]
    assert "text-truncate" in card_html[:2000]


def test_images_are_contained_by_css():
    """@spec VW-RSP-003: images can never exceed their container's width."""
    css = _css()
    main_img = _rule(css, r"\.main-content\s+img")
    assert "max-width: 100%" in main_img
    modal_img = _rule(css, r"\.modal\s+img")
    assert "max-width: 100%" in modal_img


def test_mobile_chrome_respects_safe_area_inset():
    """@spec VW-RSP-004: tab bar, FAB and content clearance use the inset."""
    css = _css()
    tabs = _rule(css, r"\.mobile-tabs")
    assert "env(safe-area-inset-bottom" in tabs
    fab_mobile = re.findall(r"\.fab\s*\{([^}]*)\}", css)
    assert any("env(safe-area-inset-bottom" in block for block in fab_mobile)
    contents = re.findall(r"\.main-content\s*\{([^}]*)\}", css)
    assert any("env(safe-area-inset-bottom" in block for block in contents)


def test_mobile_card_actions_have_44px_tap_targets():
    """@spec VW-RSP-005: card action buttons are at least 44px tall."""
    css = _css()
    actions_btn = _rule(css, r"\.item-card-actions\s+\.btn")
    assert "min-height: 44px" in actions_btn
