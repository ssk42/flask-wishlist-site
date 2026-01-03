"""Browser tests for Item CRUD operations - Create, Read, Update, Delete."""
import uuid
from playwright.sync_api import expect


def test_submit_item_page_renders(page, live_server):
    """Test submit item page renders for logged in user."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Item Creator")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Navigate to submit item
    page.goto(f"{live_server}/submit_item")
    expect(page.locator('h1:has-text("Add a new wishlist item")')).to_be_visible()
    expect(page.locator('input[name="description"]')).to_be_visible()


def test_submit_item_with_all_fields(page, live_server):
    """Test creating item with all fields populated."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Full Item Creator")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")

    item_desc = f"Full Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="link"]', "https://example.com/product")
    page.fill('input[name="price"]', "99.99")
    page.fill('input[name="category"]', "Electronics")
    page.select_option('select[name="priority"]', "High")
    page.click('button[type="submit"]')

    # Verify success
    expect(page.locator('.alert-success')).to_be_visible()
    expect(page.locator(f'text="{item_desc}"')).to_be_visible()


def test_submit_item_minimal_fields(page, live_server):
    """Test creating item with only required fields."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Minimal Creator")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")

    item_desc = f"Minimal Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')

    expect(page.locator('.alert-success')).to_be_visible()


def test_submit_item_requires_login(page, live_server):
    """Test submit item redirects to login when not authenticated."""
    page.goto(f"{live_server}/submit_item")
    expect(page).to_have_url(f"{live_server}/login?next=%2Fsubmit_item")


def test_edit_item_page_renders(page, live_server):
    """Test edit item page shows item details."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Editor")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Create item
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Editable Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="price"]', "50.00")
    page.click('button[type="submit"]')

    # Go to items and click Edit
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    item_card.locator('a:has-text("Edit")').click()

    # Verify edit page
    expect(page.locator('h1:has-text("Edit item")')).to_be_visible()
    expect(page.locator('input[name="description"]')).to_have_value(item_desc)


def test_edit_item_updates_fields(page, live_server):
    """Test editing item updates the values."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Updater")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Create item
    page.goto(f"{live_server}/submit_item")
    original_desc = f"Original Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', original_desc)
    page.click('button[type="submit"]')

    # Navigate to items page and get edit link
    page.goto(f"{live_server}/items")
    page.wait_for_load_state('networkidle')
    
    # Get the item ID from the edit link
    item_card = page.locator(f'.glass-card:has-text("{original_desc}")')
    edit_link = item_card.locator('a:has-text("Edit")')
    edit_href = edit_link.get_attribute('href')
    
    # Navigate directly to edit page
    page.goto(f"{live_server}{edit_href}")
    page.wait_for_load_state('networkidle')
    
    # Wait for the form to be fully loaded
    form = page.locator('form.glass-card')
    expect(form).to_be_visible()

    # Update fields using DOM locators
    updated_desc = f"Updated Item {uuid.uuid4().hex[:8]}"
    form.locator('input[name="description"]').fill(updated_desc)
    form.locator('input[name="price"]').fill("75.00")
    
    # Click the submit button within the form (DOM-based approach)
    submit_button = form.locator('button[type="submit"]')
    expect(submit_button).to_be_visible()
    
    with page.expect_navigation():
        submit_button.click()

    # Verify we're on the items page and the updated description appears
    assert "/items" in page.url
    expect(page.locator(f'.glass-card:has-text("{updated_desc}")')).to_be_visible()


def test_edit_item_other_user_cannot_edit_unless_claimed(page, live_server):
    """Test that other users can only edit items they've claimed."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    other_email = f"other+{uuid.uuid4().hex[:8]}@example.com"

    # Owner creates item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Owner")
    page.fill('input[name="email"]', owner_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', owner_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"Owner Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Other user logs in
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Other")
    page.fill('input[name="email"]', other_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', other_email)
    page.click('button[type="submit"]')

    # View items - should not see Edit button on other's item
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    edit_button = item_card.locator('a:has-text("Edit")')
    expect(edit_button).not_to_be_visible()


def test_delete_item_flow(page, live_server):
    """Test deleting an item."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Deleter")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Create item
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Delete Me {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')

    # Verify item exists
    page.goto(f"{live_server}/items")
    expect(page.locator(f'text="{item_desc}"')).to_be_visible()

    # Delete item
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    page.on("dialog", lambda dialog: dialog.accept())
    item_card.locator('a:has-text("Delete")').click()

    # Verify deleted
    expect(page.locator('.alert')).to_contain_text("deleted")
    expect(page.locator(f'text="{item_desc}"')).not_to_be_visible()


def test_delete_item_other_user_cannot_delete(page, live_server):
    """Test that other users cannot delete items they don't own."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    other_email = f"other+{uuid.uuid4().hex[:8]}@example.com"

    # Owner creates item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Owner")
    page.fill('input[name="email"]', owner_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', owner_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"Protected Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Other user logs in
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Other")
    page.fill('input[name="email"]', other_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', other_email)
    page.click('button[type="submit"]')

    # View items - should not see Delete button
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    delete_button = item_card.locator('a:has-text("Delete")')
    expect(delete_button).not_to_be_visible()


def test_item_with_image_url(page, live_server):
    """Test creating item with image URL."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Image User")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"Image Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="image_url"]', "https://example.com/image.jpg")
    page.click('button[type="submit"]')

    expect(page.locator('.alert-success')).to_be_visible()
