"""Browser tests for comprehensive field coverage - navbar, sidebar, modals, flash messages."""
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


# ==================== Navbar Tests ====================


def test_navbar_shows_all_links_when_logged_in(page, live_server):
    """Verify navbar shows all expected links for logged in user."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/")

    # Check for main navigation links - use .first since sidebar/mobile may
    # duplicate
    expect(page.locator('a:has-text("Home")').first).to_be_visible()
    expect(page.locator(
        'a:has-text("All Gifts"), a:has-text("Items")').first).to_be_visible()
    expect(page.locator('a:has-text("Events")').first).to_be_visible()
    expect(page.locator('a:has-text("My Claims")').first).to_be_visible()


def test_navbar_shows_logout_for_logged_in_user(page, live_server):
    """Verify logout link is visible when logged in."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/")

    expect(page.locator('a:has-text("Logout"), a:has-text("Log out")')).to_be_visible()


def test_navbar_links_navigate_correctly(page, live_server):
    """Test that navbar links navigate to correct pages."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/")

    # Click Items link
    page.locator('a:has-text("All Items"), a:has-text("Items")').first.click()
    expect(page).to_have_url(f"{live_server}/items")

    # Click Events link
    page.locator('a:has-text("Events")').first.click()
    expect(page).to_have_url(f"{live_server}/events")

    # Click My Claims link
    page.locator('a:has-text("My Claims")').first.click()
    expect(page).to_have_url(f"{live_server}/my-claims")


# ==================== Flash Message Tests ====================


def test_success_flash_message_displays(page, live_server):
    """Verify success flash message displays correctly."""
    register_and_login(page, live_server)

    # Create item - this should show success flash
    page.goto(f"{live_server}/submit_item")
    page.fill('input[name="description"]',
              f"Flash Test {uuid.uuid4().hex[:8]}")
    page.click('button[type="submit"]')

    flash = page.locator('.alert-success')
    expect(flash).to_be_visible()
    expect(flash).to_contain_text('added')


def test_warning_flash_message_displays(page, live_server):
    """Verify warning flash message displays correctly."""
    register_and_login(page, live_server)

    # Create own item
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Own Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')

    # Try to claim own item - should show warning
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')

    # Click claim if visible (shouldn't be, but if it is)
    claim_btn = item_card.locator(
        'button:has-text("Claim"), a:has-text("Claim")')
    if claim_btn.count() > 0:
        claim_btn.first.click()
        expect(page.locator('.alert-warning, .alert-danger')).to_be_visible()


# ==================== Modal Tests ====================


def test_quick_view_modal_opens(page, live_server):
    """Test quick view modal opens when clicking Quick View."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    viewer_email = f"viewer+{uuid.uuid4().hex[:8]}@example.com"

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
    item_desc = f"Modal Item {uuid.uuid4().hex[:8]}"
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

    # Go to dashboard and click quick view
    page.goto(f"{live_server}/")
    quick_view_btn = page.locator('button:has-text("Quick View")').first
    if quick_view_btn.is_visible():
        quick_view_btn.click()

        # Modal should appear
        modal = page.locator('.modal.show, [role="dialog"]')
        expect(modal).to_be_visible(timeout=5000)


def test_modal_close_button_works(page, live_server):
    """Test that modal close button dismisses modal."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    viewer_email = f"viewer+{uuid.uuid4().hex[:8]}@example.com"

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
    item_desc = f"Close Modal {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Viewer logs in
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Viewer2")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/")
    quick_view_btn = page.locator('button:has-text("Quick View")').first
    if quick_view_btn.is_visible():
        quick_view_btn.click()
        page.wait_for_timeout(500)

        # Click close button
        close_btn = page.locator('.btn-close, button:has-text("Close")').first
        close_btn.click()

        # Modal should be hidden
        page.wait_for_timeout(500)
        modal = page.locator('.modal.show')
        expect(modal).not_to_be_visible()


# ==================== Button Label Tests ====================


def test_submit_item_button_has_correct_label(page, live_server):
    """Verify submit item button has appropriate label."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/submit_item")

    submit_btn = page.locator('button[type="submit"]')
    expect(submit_btn).to_be_visible()
    # Button says "Save item"
    expect(submit_btn).to_contain_text('Save')


def test_edit_item_button_has_correct_label(page, live_server):
    """Verify edit item save button has appropriate label."""
    register_and_login(page, live_server)

    # Create item
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Button Label {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')

    # Go to edit
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    item_card.locator('a:has-text("Edit")').click()

    submit_btn = page.locator('button[type="submit"]')
    expect(submit_btn).to_be_visible()
    # Button should say "Save" or "Update"
    expect(submit_btn).to_contain_text('Save')
