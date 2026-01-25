"""Comprehensive browser tests for Dashboard (index page)."""
import uuid
from playwright.sync_api import expect


def test_dashboard_shows_other_users_items(page, live_server):
    """Test dashboard shows items from other users."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    viewer_email = f"viewer+{uuid.uuid4().hex[:8]}@example.com"

    # Owner creates items
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Owner")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"Dashboard Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Viewer logs in
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Viewer")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Dashboard should show owner's item
    page.goto(f"{live_server}/")
    expect(page.locator(f'text="{item_desc}"')).to_be_visible()


def test_dashboard_hides_own_items(page, live_server):
    """Test dashboard does not show user's own items in the feed."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Solo User")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"My Own Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')

    # Dashboard should not show own items (shows other users' items only)
    page.goto(f"{live_server}/")
    # The item should not be visible on dashboard since it's the user's own
    expect(page.locator(
        f'.glass-card:has-text("{item_desc}")')).not_to_be_visible()


def test_dashboard_quick_view_modal(page, live_server):
    """Test quick view modal on dashboard."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    viewer_email = f"viewer+{uuid.uuid4().hex[:8]}@example.com"

    # Owner creates item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Modal Owner")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"Modal Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="price"]', "199.99")
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Viewer opens modal
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Modal Viewer")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    item_card.locator('button[title="Quick View"]').click()

    # Modal should be visible with item details
    modal = page.locator('#quickViewModal')
    expect(modal).to_be_visible()
    expect(modal).to_contain_text(item_desc)


def test_dashboard_navbar_links(page, live_server):
    """Test all navbar links are visible and work."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Navbar User")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/")

    # Check sidebar links (text is inside .sidebar-link-text spans)
    expect(page.locator('.sidebar-link-text:has-text("Home")').first).to_be_visible()
    expect(page.locator(
        '.sidebar-link-text:has-text("All Gifts")').first).to_be_visible()
    expect(page.locator('.sidebar-link-text:has-text("Events")').first).to_be_visible()
    expect(page.locator(
        '.sidebar-link-text:has-text("My Claims")').first).to_be_visible()


def test_dashboard_shows_priority_badges(page, live_server):
    """Test dashboard shows priority badges on items."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    viewer_email = f"viewer+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Priority Owner")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"High Priority {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.select_option('select[name="priority"]', "High")
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Priority Viewer")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    expect(item_card.locator('.badge:has-text("High")')).to_be_visible()


def test_dashboard_shows_price(page, live_server):
    """Test dashboard shows item prices."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    viewer_email = f"viewer+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Price Owner")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"Priced Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="price"]', "149.99")
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Price Viewer")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    expect(item_card.locator('text="$149.99"')).to_be_visible()


def test_dashboard_external_link(page, live_server):
    """Test dashboard shows external link button for items with links."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    viewer_email = f"viewer+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Link Owner")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"Linked Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="link"]', "https://example.com/product")
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Link Viewer")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    # External link button should be visible
    expect(item_card.locator('a[title="Visit Link"]')).to_be_visible()
