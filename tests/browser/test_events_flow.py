"""Browser tests for the Events feature."""
import uuid
from datetime import date, timedelta

from playwright.sync_api import expect


def test_create_event_flow(page, live_server):
    """Test creating a new event."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Event Creator")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Navigate to events page
    page.goto(f"{live_server}/events")
    expect(page.locator('h2:has-text("Events")')).to_be_visible()

    # Click new event button
    page.click('a:has-text("New Event")')
    expect(page).to_have_url(f"{live_server}/events/new")

    # Fill in event form
    future_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    page.fill('input[name="name"]', "Birthday Party")
    page.fill('input[name="date"]', future_date)
    page.click('button[type="submit"]')

    # Verify success
    expect(page.locator('.alert-success')).to_contain_text("created successfully")
    expect(page.locator('h3:has-text("Birthday Party")')).to_be_visible()


def test_edit_event_flow(page, live_server):
    """Test editing an existing event."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Event Editor")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Create an event first
    page.goto(f"{live_server}/events/new")
    future_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    page.fill('input[name="name"]', "Original Event")
    page.fill('input[name="date"]', future_date)
    page.click('button[type="submit"]')

    # Click edit on the event
    page.click('a:has-text("Edit")')

    # Update the event name
    page.fill('input[name="name"]', "Updated Event")
    page.click('button[type="submit"]')

    # Verify update
    expect(page.locator('.alert-success')).to_contain_text("updated successfully")
    expect(page.locator('h3:has-text("Updated Event")')).to_be_visible()


def test_delete_event_flow(page, live_server):
    """Test deleting an event."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Event Deleter")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Create an event first
    page.goto(f"{live_server}/events/new")
    future_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    page.fill('input[name="name"]', "Event to Delete")
    page.fill('input[name="date"]', future_date)
    page.click('button[type="submit"]')

    # Handle the confirm dialog and click delete
    page.on("dialog", lambda dialog: dialog.accept())
    page.click('button:has-text("Delete")')

    # Verify deletion
    expect(page.locator('.alert')).to_contain_text("deleted")
    expect(page.locator('h3:has-text("Event to Delete")')).not_to_be_visible()


def test_events_navbar_link_visible(page, live_server):
    """Test that Events link appears in navbar for logged-in users."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Test User")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Check navbar has Events link
    page.goto(f"{live_server}/")
    expect(page.locator('a:has-text("Events")')).to_be_visible()


def test_events_requires_login(page, live_server):
    """Test that Events page redirects to login when not authenticated."""
    page.goto(f"{live_server}/events")

    # Should redirect to login
    expect(page).to_have_url(f"{live_server}/login?next=%2Fevents")


def test_submit_item_with_event_association(page, live_server):
    """Test that items can be associated with events."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Item Creator")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Create an event first
    page.goto(f"{live_server}/events/new")
    future_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    page.fill('input[name="name"]', "Christmas 2025")
    page.fill('input[name="date"]', future_date)
    page.click('button[type="submit"]')

    # Create an item with event association
    page.goto(f"{live_server}/submit_item")
    page.fill('input[name="description"]', "Gift for Christmas")
    # Select the event by index (index 1 = first event after "No event")
    page.select_option('select[name="event_id"]', index=1)
    page.click('button[type="submit"]')

    # Verify item was created
    expect(page.locator('.alert-success')).to_be_visible()
