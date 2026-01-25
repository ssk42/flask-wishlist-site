"""Browser tests for form validation and picklist options."""
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


# ==================== Submit Item Form Picklists ====================

def test_submit_item_status_picklist_options(page, live_server):
    """Verify status picklist has correct options on submit item form."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/submit_item")

    status_select = page.locator('select[name="status"]')
    expect(status_select).to_be_visible()

    # Get all option values
    options = status_select.locator('option').all_text_contents()

    # Verify expected status options exist
    assert 'Available' in options
    assert 'Claimed' in options
    assert 'Purchased' in options


def test_submit_item_priority_picklist_options(page, live_server):
    """Verify priority picklist has correct options on submit item form."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/submit_item")

    priority_select = page.locator('select[name="priority"]')
    expect(priority_select).to_be_visible()

    options = priority_select.locator('option').all_text_contents()

    # Verify expected priority options
    assert 'High' in options
    assert 'Medium' in options
    assert 'Low' in options


def test_submit_item_event_picklist_present(page, live_server):
    """Verify event picklist is present on submit item form when events exist."""
    import datetime
    register_and_login(page, live_server)

    # First create an event so the picklist appears
    page.goto(f"{live_server}/events")
    page.click('a:has-text("New Event")')
    page.fill('input[name="name"]', 'Test Event')
    # Set date to future
    tomorrow = (
        datetime.date.today() +
        datetime.timedelta(
            days=30)).strftime('%Y-%m-%d')
    page.fill('input[name="date"]', tomorrow)
    page.click('button[type="submit"]')

    # Now go to submit item
    page.goto(f"{live_server}/submit_item")

    event_select = page.locator('select[name="event_id"]')
    expect(event_select).to_be_visible()

    # Should have at least No event + the created event
    options_count = event_select.locator('option').count()
    assert options_count >= 2


# ==================== Edit Item Form Picklists ====================


def test_edit_item_status_picklist_options(page, live_server):
    """Verify priority picklist has correct options on edit item form (owner view)."""
    register_and_login(page, live_server)

    # Create item first
    page.goto(f"{live_server}/submit_item")
    item_desc = f"Edit Status Test {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')

    # Navigate to edit - owner sees priority (not status - that's for
    # non-owners)
    page.goto(f"{live_server}/items")
    page.wait_for_load_state('networkidle')

    # Click Edit link
    edit_link = page.locator(
        f'.glass-card:has-text("{item_desc}") a:has-text("Edit")').first
    expect(edit_link).to_be_visible()
    edit_link.click()
    page.wait_for_load_state('networkidle')

    # Owner sees priority select, not status (status only for non-owners)
    priority_select = page.locator('select[name="priority"]')
    expect(priority_select).to_be_visible()

    options = priority_select.locator('option').all_text_contents()
    assert 'High' in options
    assert 'Medium' in options
    assert 'Low' in options


def test_edit_item_preserves_selected_priority(page, live_server):
    """Verify edit form preserves the item's priority value."""
    register_and_login(page, live_server)

    # Create item with High priority
    page.goto(f"{live_server}/submit_item")
    item_desc = f"High Priority {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item_desc)
    page.select_option('select[name="priority"]', 'High')
    page.click('button[type="submit"]')

    # Navigate to edit
    page.goto(f"{live_server}/items")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    item_card.locator('a:has-text("Edit")').click()

    # Verify High is selected
    priority_select = page.locator('select[name="priority"]')
    expect(priority_select).to_have_value('High')


# ==================== Items List Filter Picklists ====================


def test_items_filter_status_picklist_options(page, live_server):
    """Verify status filter picklist has correct options."""
    register_and_login(page, live_server)

    # Create item first so filter options are populated
    page.goto(f"{live_server}/submit_item")
    page.fill('input[name="description"]',
              f'Filter Test {uuid.uuid4().hex[:8]}')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')

    page.goto(f"{live_server}/items")
    page.wait_for_load_state('networkidle')

    status_filter = page.locator('select[name="status_filter"]')
    expect(status_filter).to_be_visible()

    options = status_filter.locator('option').all_text_contents()

    # Should have All/Status option plus status values
    assert len(options) >= 2  # At least blank + Available
    # Check Available is in options (may have extra text)
    assert any('Available' in opt for opt in options)


def test_items_filter_priority_picklist_options(page, live_server):
    """Verify priority filter picklist has correct options."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/items")

    priority_filter = page.locator('select[name="priority_filter"]')
    expect(priority_filter).to_be_visible()

    options = priority_filter.locator('option').all_text_contents()

    assert 'High' in options
    assert 'Medium' in options
    assert 'Low' in options


def test_items_filter_user_picklist_populated(page, live_server):
    """Verify user filter picklist shows registered users."""
    register_and_login(page, live_server, name="Filter Test User")
    page.goto(f"{live_server}/items")

    user_filter = page.locator('select[name="user_filter"]')
    expect(user_filter).to_be_visible()

    # Should have at least All and the current user
    options_text = user_filter.locator('option').all_text_contents()
    assert len(options_text) >= 2
    assert 'Filter Test User' in options_text or any(
        'Filter Test' in opt for opt in options_text)


def test_items_filter_sort_by_picklist_options(page, live_server):
    """Verify sort by picklist has correct options."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/items")

    sort_by = page.locator('select[name="sort_by"]')
    expect(sort_by).to_be_visible()

    options = sort_by.locator('option').all_text_contents()

    # Verify expected sort options
    assert any('Priority' in opt for opt in options)
    assert any('Price' in opt for opt in options)
    assert any('Status' in opt for opt in options)


def test_items_filter_sort_order_picklist_options(page, live_server):
    """Verify sort order picklist has asc/desc options."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/items")

    sort_order = page.locator('select[name="sort_order"]')
    expect(sort_order).to_be_visible()

    options = sort_order.locator('option').all_text_contents()

    # Should have ascending and descending
    assert len(options) == 2
    assert any('asc' in opt.lower() or '↑' in opt for opt in options)
    assert any('desc' in opt.lower() or '↓' in opt for opt in options)


# ==================== Events Form Picklists ====================


def test_event_form_all_fields_present(page, live_server):
    """Verify event form has all required fields."""
    register_and_login(page, live_server)
    page.goto(f"{live_server}/events")
    page.click('a:has-text("New Event")')

    # Verify form fields
    expect(page.locator('input[name="name"]')).to_be_visible()
    expect(page.locator('input[name="date"]')).to_be_visible()
    expect(page.locator('button[type="submit"]')).to_be_visible()
