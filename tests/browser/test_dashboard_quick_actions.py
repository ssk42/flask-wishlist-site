"""Browser tests for the Dashboard Quick Actions feature."""
import uuid
import pytest
from playwright.sync_api import expect

def test_quick_claim_flow(page, live_server):
    """Test claiming an item directly from the dashboard."""
    # User A credentials
    user_a_email = f"user_a+{uuid.uuid4().hex[:8]}@example.com"
    user_a_name = "User A"

    # User B credentials
    user_b_email = f"user_b+{uuid.uuid4().hex[:8]}@example.com"
    user_b_name = "User B"

    # 1. Register and Login as User A to create an item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', user_a_name)
    page.fill('input[name="email"]', user_a_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_a_email)
    page.click('button[type="submit"]')

    # User A creates an item
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Cool Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    # Logout User A
    page.goto(f"{live_server}/logout")

    # 2. Register and Login as User B
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', user_b_name)
    page.fill('input[name="email"]', user_b_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_b_email)
    page.click('button[type="submit"]')

    # 3. User B views dashboard and sees User A's item
    page.goto(f"{live_server}/")
    expect(page.locator(f'h3:has-text("{item_desc}")')).to_be_visible()

    # 4. User B clicks "Claim"
    # Find the claim button for this specific item
    # We look for the card containing the text, then find the claim button within it
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')

    # Use a more specific selector - the Claim button has outline-primary class
    claim_button = item_card.locator('button.btn-outline-primary:has-text("Claim")')

    # Handle the confirm dialog
    page.on("dialog", lambda dialog: dialog.accept())
    claim_button.click()

    # 5. Verify the card updates (HTMX swap)
    # After claiming, the claimer sees an "Unclaim" button (outline-warning class)
    unclaim_button = item_card.locator('button.btn-outline-warning:has-text("Unclaim")')
    expect(unclaim_button).to_be_visible()
    expect(claim_button).not_to_be_visible()

def test_quick_view_flow(page, live_server):
    """Test viewing item details in a modal from the dashboard."""
    # User A credentials
    user_a_email = f"user_a+{uuid.uuid4().hex[:8]}@example.com"
    user_a_name = "User A"
    
    # User B credentials
    user_b_email = f"user_b+{uuid.uuid4().hex[:8]}@example.com"
    
    # 1. Register/Login User A and create item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', user_a_name)
    page.fill('input[name="email"]', user_a_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_a_email)
    page.click('button[type="submit"]')
    
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Modal Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    # Notes field does not exist in the form
    # page.fill('input[name="notes"]', "Some detailed notes about this item.")
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # 2. Login User B
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "User B")
    page.fill('input[name="email"]', user_b_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_b_email)
    page.click('button[type="submit"]')

    # 3. Open Quick View
    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    # Use the attribute title="Quick View" or the icon class
    quick_view_btn = item_card.locator('button[title="Quick View"]')
    quick_view_btn.click()

    # 4. Verify Modal opens and contains details
    modal = page.locator('#quickViewModal')
    expect(modal).to_be_visible()
    expect(modal).to_contain_text(item_desc)
    # Notes are not part of the form anymore
    # expect(modal).to_contain_text("Some detailed notes about this item.")

    # 5. Close Modal
    modal.locator('button[data-bs-dismiss="modal"]').click()
    expect(modal).not_to_be_visible()
