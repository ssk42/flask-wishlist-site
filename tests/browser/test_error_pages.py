"""Browser tests for error pages (403, 404, 500)."""
import uuid
from playwright.sync_api import expect


def register_and_login(page, live_server, name="Test User"):
    """Helper to register and login a new user."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', name)
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    return user_email


def test_404_page_renders_for_invalid_url(page, live_server):
    """Verify 404 page renders for non-existent routes."""
    register_and_login(page, live_server)

    response = page.goto(f"{live_server}/this-page-does-not-exist")

    # Should return 404 status
    assert response.status == 404

    # Should display error page content
    expect(page.locator('text=404')).to_be_visible()


def test_404_page_has_home_link(page, live_server):
    """Verify 404 page has a link to go home."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/nonexistent-page")

    # Should have a way to go back home
    home_link = page.locator(
        'a:has-text("home"), a:has-text("Home"), a:has-text("Go Back")')
    expect(home_link.first).to_be_visible()


def test_404_for_nonexistent_item(page, live_server):
    """Verify 404 when accessing non-existent item."""
    register_and_login(page, live_server)

    response = page.goto(f"{live_server}/edit_item/999999")

    assert response.status == 404


def test_404_for_nonexistent_event(page, live_server):
    """Verify 404 when accessing non-existent event."""
    register_and_login(page, live_server)

    response = page.goto(f"{live_server}/event/999999/edit")

    # Should be 404 or redirect
    assert response.status == 404 or response.status == 302
