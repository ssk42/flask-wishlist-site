"""Browser tests for the My Claims feature."""
import uuid

from playwright.sync_api import expect


def test_my_claims_page_loads_when_empty(page, live_server):
    """Test that My Claims page loads correctly when no claims exist."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Test User")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Navigate to My Claims page
    page.goto(f"{live_server}/my-claims")

    # Verify the page loads with appropriate empty state message
    expect(page.locator('h1:has-text("My Claims")')).to_be_visible()
    expect(page.locator('text=No claimed items yet')).to_be_visible()


def test_my_claims_navbar_link_visible_when_logged_in(page, live_server):
    """Test that My Claims link appears in navbar for logged-in users."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Test User")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Check navbar has My Claims link
    page.goto(f"{live_server}/")
    expect(page.locator('a:has-text("My Claims")')).to_be_visible()


def test_my_claims_requires_login(page, live_server):
    """Test that My Claims page redirects to login when not authenticated."""
    page.goto(f"{live_server}/my-claims")

    # Should redirect to login
    expect(page).to_have_url(f"{live_server}/login?next=%2Fmy-claims")
