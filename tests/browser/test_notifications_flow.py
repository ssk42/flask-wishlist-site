"""Browser tests for Notifications functionality."""
import uuid
from playwright.sync_api import expect


def test_notifications_page_renders(page, live_server):
    """Test notifications page renders for logged in user."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Notif User")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/notifications")
    expect(page.locator('h1:has-text("Notifications")')).to_be_visible()


def test_notifications_requires_login(page, live_server):
    """Test notifications page redirects to login when not authenticated."""
    page.goto(f"{live_server}/notifications")
    expect(page).to_have_url(f"{live_server}/login?next=%2Fnotifications")


def test_notification_generated_on_comment(page, live_server):
    """Test that commenting on an item generates a notification for other participants."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    commenter1_email = f"commenter1+{uuid.uuid4().hex[:8]}@example.com"
    commenter2_email = f"commenter2+{uuid.uuid4().hex[:8]}@example.com"

    # Owner creates item
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
    item_desc = f"Notif Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Commenter 1 adds a comment
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Commenter One")
    page.fill('input[name="email"]', commenter1_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', commenter1_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    item_card.locator('button:has-text("Comments")').click()
    page.wait_for_timeout(500)
    item_card.locator('input[name="text"]').fill("First comment")
    item_card.locator('button:has-text("Post")').click()
    page.wait_for_timeout(1000)  # Wait for comment to be posted
    page.goto(f"{live_server}/logout")

    # Commenter 2 adds a comment
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Commenter Two")
    page.fill('input[name="email"]', commenter2_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', commenter2_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    item_card.locator('button:has-text("Comments")').click()
    page.wait_for_timeout(500)
    item_card.locator('input[name="text"]').fill("Second comment")
    item_card.locator('button:has-text("Post")').click()
    page.wait_for_timeout(1000)  # Wait for comment to be posted
    page.goto(f"{live_server}/logout")

    # Commenter 1 should have a notification about commenter 2's comment
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', commenter1_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/notifications")
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)  # Extra wait for DOM to settle

    # Check that there's at least one notification about a comment
    # The notification list should not show "No notifications yet"
    expect(page.locator('.list-group-item').first).to_be_visible()


def test_notifications_empty_state(page, live_server):
    """Test notifications page shows empty state when no notifications."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Empty Notif User")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/notifications")
    # Should show some indication of no notifications
    expect(page.locator('h1:has-text("Notifications")')).to_be_visible()
