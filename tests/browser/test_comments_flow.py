"""Browser tests for Comments functionality."""
import uuid
from playwright.sync_api import expect


def test_add_comment_to_item(page, live_server):
    """Test adding a comment to another user's item."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    commenter_email = f"commenter+{uuid.uuid4().hex[:8]}@example.com"

    # Register owner and create item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Item Owner")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"Commentable Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Register commenter
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Commenter")
    page.fill('input[name="email"]', commenter_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', commenter_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Go to items list and find the item card
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')

    # Expand comments section by clicking the Comments button
    comments_button = item_card.locator('button:has-text("Comments")')
    comments_button.click()

    # Wait for collapse animation
    page.wait_for_timeout(500)

    # Fill in comment and post
    comment_text = f"Test comment {uuid.uuid4().hex[:8]}"
    item_card.locator('input[name="text"]').fill(comment_text)
    item_card.locator('button:has-text("Post")').click()

    # Verify success flash message
    expect(page.locator('.alert-success')).to_be_visible()


def test_cannot_comment_on_own_item(page, live_server):
    """Test that comments section is not visible for own items."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Self Commenter")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Create an item
    page.goto(f"{live_server}/submit_item")
    item_desc = f"My Own Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')

    # Go to items list
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')

    # Comments section should not be visible for own items
    comments_button = item_card.locator('button:has-text("Comments")')
    expect(comments_button).not_to_be_visible()
