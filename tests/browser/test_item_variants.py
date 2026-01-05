"""Browser tests for item variant fields (size, color, quantity)."""
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


def test_submit_item_shows_variant_fields(page, live_server):
    """Verify submit item form shows size, color, quantity fields."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/submit_item")
    
    # Verify variant fields are present
    expect(page.locator('input[name="size"]')).to_be_visible()
    expect(page.locator('input[name="color"]')).to_be_visible()
    expect(page.locator('input[name="quantity"]')).to_be_visible()


def test_submit_item_with_size_color_quantity(page, live_server):
    """Test creating item with all variant fields."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/submit_item")
    
    item_desc = f"Variant Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="size"]', 'Large')
    page.fill('input[name="color"]', 'Navy Blue')
    page.fill('input[name="quantity"]', '3')
    page.fill('input[name="price"]', '49.99')
    page.click('button[type="submit"]')
    
    # Verify success
    expect(page.locator('.alert-success')).to_be_visible()
    
    # Verify item appears with variants visible
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    expect(item_card).to_be_visible()
    
    # Check that variant info is displayed (size/color/qty badges)
    expect(item_card.locator('text=Large')).to_be_visible()
    expect(item_card.locator('text=Navy Blue')).to_be_visible()


def test_edit_item_shows_variant_values(page, live_server):
    """Verify edit form shows saved variant values."""
    register_and_login(page, live_server)
    
    # Create item with variants
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Edit Variant {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="size"]', 'Medium')
    page.fill('input[name="color"]', 'Red')
    page.fill('input[name="quantity"]', '2')
    page.click('button[type="submit"]')
    
    # Navigate to edit
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    item_card.locator('a:has-text("Edit")').click()
    
    # Verify variant values are preserved
    expect(page.locator('input[name="size"]')).to_have_value('Medium')
    expect(page.locator('input[name="color"]')).to_have_value('Red')
    expect(page.locator('input[name="quantity"]')).to_have_value('2')


def test_edit_item_updates_variants(page, live_server):
    """Test updating variant values via edit form."""
    register_and_login(page, live_server)
    
    # Create item
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Update Variant {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="size"]', 'Small')
    page.click('button[type="submit"]')
    
    # Edit and update variants
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    item_card.locator('a:has-text("Edit")').click()
    
    page.fill('input[name="size"]', 'XL')
    page.fill('input[name="color"]', 'Green')
    page.fill('input[name="quantity"]', '5')
    page.click('button[type="submit"]')
    
    # Verify updates
    expect(page.locator('.alert-success')).to_be_visible()
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    expect(item_card.locator('text=XL')).to_be_visible()
    expect(item_card.locator('text=Green')).to_be_visible()


def test_variant_quantity_validation_error(page, live_server):
    """Test quantity validation shows error for invalid values."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/submit_item")
    
    page.fill('input[name="description"]', 'Invalid Quantity Item')
    
    # Use JavaScript to set quantity value bypassing HTML5 max validation
    page.evaluate("document.querySelector('input[name=\"quantity\"]').value = '100'")
    
    # Remove the max attribute to allow form submission
    page.evaluate("document.querySelector('input[name=\"quantity\"]').removeAttribute('max')")
    
    page.click('button[type="submit"]')
    
    # Should stay on submit page with validation error
    page.wait_for_load_state('networkidle')
    
    # Look for the validation error message anywhere on page
    page_content = page.content()
    assert 'Quantity must be between 1 and 99' in page_content


def test_item_card_displays_variants(page, live_server):
    """Verify item card shows variant badges."""
    register_and_login(page, live_server)
    
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Badge Variant {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.fill('input[name="size"]', 'XXL')
    page.fill('input[name="color"]', 'Purple')
    page.fill('input[name="quantity"]', '4')
    page.click('button[type="submit"]')
    
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    
    # Verify variant badges are displayed
    # Look for the variant section with badges
    expect(item_card).to_contain_text('XXL')
    expect(item_card).to_contain_text('Purple')
    expect(item_card).to_contain_text('4')
