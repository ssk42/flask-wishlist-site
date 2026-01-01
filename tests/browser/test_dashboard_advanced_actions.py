
import uuid
import pytest
from playwright.sync_api import expect

def test_modal_claim_flow_and_flash(page, live_server):
    """Test claiming an item from the Quick View modal and verifying the flash message."""
    # User A credentials
    user_a_email = f"user_a+{uuid.uuid4().hex[:8]}@example.com"
    user_a_name = "User A"
    
    # User B credentials
    user_b_email = f"user_b+{uuid.uuid4().hex[:8]}@example.com"
    user_b_name = "User B"
    
    # 1. Register/Login User A and create item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', user_a_name)
    page.fill('input[name="email"]', user_a_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_a_email)
    page.click('button[type="submit"]')
    
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Modal Claim Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # 2. Login User B
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', user_b_name)
    page.fill('input[name="email"]', user_b_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_b_email)
    page.click('button[type="submit"]')

    # 3. Open Quick View
    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    quick_view_btn = item_card.locator('button[title="Quick View"]')
    quick_view_btn.click()

    # 4. Wait for Modal and Click Claim
    modal = page.locator('#quickViewModal')
    expect(modal).to_be_visible()
    
    # Verify Claim Button exists
    claim_btn = modal.locator('button:has-text("Claim This Item")')
    expect(claim_btn).to_be_visible()
    
    # Click Claim
    claim_btn.click()

    # 5. Verify Modal Closes
    expect(modal).not_to_be_visible()

    # 6. Verify Card Updates (Background Swap)
    expect(item_card.locator('span.badge:has-text("Claimed")')).to_be_visible()

    # 7. Verify Flash Message Appears
    flash_message = page.locator('.alert.alert-success')
    expect(flash_message).to_be_visible()
    expect(flash_message).to_contain_text(f'You have claimed "{item_desc}"')


def test_unclaim_flow(page, live_server):
    """Test claiming and then unclaiming an item from the dashboard."""
    # User A (Owner)
    user_a_email = f"user_a+{uuid.uuid4().hex[:8]}@example.com"
    user_a_name = "User A"
    
    # User B (Claimer)
    user_b_email = f"user_b+{uuid.uuid4().hex[:8]}@example.com"
    user_b_name = "User B"
    
    # 1. Setup Item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', user_a_name)
    page.fill('input[name="email"]', user_a_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_a_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Unclaim Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # 2. Login User B
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', user_b_name)
    page.fill('input[name="email"]', user_b_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_b_email)
    page.click('button[type="submit"]')

    # 3. Claim Item (Quick Claim)
    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    
    # Handle Confirm Dialog for Claim (if added)
    page.on("dialog", lambda dialog: dialog.accept())
    
    item_card.locator('button:has-text("Claim")').click()
    
    # Verify Claimed
    expect(item_card.locator('button:has-text("Unclaim")')).to_be_visible()
    expect(page.locator('.alert.alert-success')).to_contain_text("You have claimed")

    # 4. Unclaim Item
    item_card.locator('button:has-text("Unclaim")').click()

    # 5. Verify Available Again
    expect(item_card.locator('button:has-text("Claim")')).to_be_visible()
    
    # Verify Flash Message for Unclaim
    # Note: Logic sends 'info' for unclaim
    expect(page.locator('.alert.alert-info')).to_contain_text("You have unclaimed")
