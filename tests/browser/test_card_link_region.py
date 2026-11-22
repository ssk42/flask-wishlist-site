"""Browser tests for the clickable card link region (GIV-CLM-022)."""
import uuid
from playwright.sync_api import expect


def _register_and_login(page, live_server, name, email):
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="email"]', email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="name"]', name)
    page.click('button[type="submit"]')


def test_card_image_and_title_open_item_link(page, live_server):
    """Clicking the region above Claim opens the item link in a new tab,
    while the Claim button itself still claims."""
    suffix = uuid.uuid4().hex[:8]
    link = f"https://example.com/gift-{suffix}"
    item_desc = f"Linked Gift {suffix}"

    _register_and_login(page, live_server, "Owner", f"owner+{suffix}@example.com")
    page.goto(f"{live_server}/submit_item")
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="link"]', link)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    _register_and_login(page, live_server, "Claimer", f"claimer+{suffix}@example.com")

    # Full card on /items: clicking the image opens the link in a new tab.
    page.goto(f"{live_server}/items")
    card = page.locator(f'.glass-card:has-text("{item_desc}")')
    expect(card).to_be_visible()
    with page.expect_popup() as popup_info:
        card.locator("img").first.click()
    popup = popup_info.value
    popup.wait_for_load_state()
    assert "example.com" in popup.url
    popup.close()

    # Dashboard card: clicking the title opens the link too.
    page.goto(f"{live_server}/")
    dash_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    expect(dash_card).to_be_visible()
    with page.expect_popup() as popup_info:
        dash_card.locator("h3").first.click()
    popup = popup_info.value
    popup.wait_for_load_state()
    assert "example.com" in popup.url
    popup.close()

    # The Claim button in the footer still claims (no navigation).
    claim_button = dash_card.locator('button.btn-outline-primary:has-text("Claim")')
    claim_button.click()
    unclaim_button = dash_card.locator('button.btn-outline-warning:has-text("Unclaim")')
    expect(unclaim_button).to_be_visible()
