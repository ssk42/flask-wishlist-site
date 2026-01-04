"""Browser tests for Claim and Unclaim item functionality."""
import uuid
from playwright.sync_api import expect


def test_claim_and_unclaim_item(page, live_server):
    """Test the full claim and unclaim flow."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    claimer_email = f"claimer+{uuid.uuid4().hex[:8]}@example.com"

    # Register owner and create item
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
    item_desc = f"Claimable Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Register claimer
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Claimer")
    page.fill('input[name="email"]', claimer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', claimer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Claim the item from dashboard
    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    claim_button = item_card.locator('button.btn-outline-primary:has-text("Claim")')
    expect(claim_button).to_be_visible()
    claim_button.click()

    # Wait for HTMX update and verify Unclaim button appears
    unclaim_button = item_card.locator('button.btn-outline-warning:has-text("Unclaim")')
    expect(unclaim_button).to_be_visible()
    expect(claim_button).not_to_be_visible()

    # Now unclaim the item
    unclaim_button.click()

    # Wait for HTMX update and verify Claim button reappears
    claim_button = item_card.locator('button.btn-outline-primary:has-text("Claim")')
    expect(claim_button).to_be_visible()


def test_cannot_claim_own_item(page, live_server):
    """Test that users cannot claim their own items."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Self Claimer")
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

    # Go to dashboard - own item should not have Claim button
    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    claim_button = item_card.locator('button:has-text("Claim")')
    expect(claim_button).not_to_be_visible()


def test_mark_as_purchased_via_edit(page, live_server):
    """Test marking an item as purchased via the edit page after claiming."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    purchaser_email = f"purchaser+{uuid.uuid4().hex[:8]}@example.com"

    # Register owner and create item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Gift Receiver")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"Purchase Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Register purchaser
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Gift Giver")
    page.fill('input[name="email"]', purchaser_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', purchaser_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Claim item from dashboard
    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    claim_button = item_card.locator('button.btn-outline-primary:has-text("Claim")')
    claim_button.click()

    # Wait for HTMX update
    page.wait_for_timeout(500)

    # Go to items list and click "Update Status" to edit the item
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    update_button = item_card.locator('a:has-text("Update Status")')
    update_button.click()

    # On edit page, change status to Purchased
    page.select_option('select[name="status"]', "Purchased")
    page.click('button[type="submit"]')

    # Verify success flash
    expect(page.locator('.alert-success')).to_be_visible()


def test_claim_from_items_list(page, live_server):
    """Test claiming an item from the items list page."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    claimer_email = f"claimer+{uuid.uuid4().hex[:8]}@example.com"

    # Register owner and create item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "List Owner")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', owner_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item_desc = f"List Claim Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Register claimer
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "List Claimer")
    page.fill('input[name="email"]', claimer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', claimer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Go to items list and claim (uses glass-card, not table rows)
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    claim_button = item_card.locator('button:has-text("Claim")')
    expect(claim_button).to_be_visible()

    # Handle the confirm dialog and click claim
    page.on("dialog", lambda dialog: dialog.accept())
    claim_button.click()

    # Wait for HTMX update and verify Unclaim button appears
    unclaim_button = item_card.locator('button:has-text("Unclaim")')
    expect(unclaim_button).to_be_visible()
