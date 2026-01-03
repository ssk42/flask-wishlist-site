"""Browser tests for Items list filtering and sorting functionality."""
import uuid
from playwright.sync_api import expect


def test_filter_items_by_user(page, live_server):
    """Test filtering items by user."""
    # Create two users with items
    user_a_email = f"user_a+{uuid.uuid4().hex[:8]}@example.com"
    user_b_email = f"user_b+{uuid.uuid4().hex[:8]}@example.com"

    # Register User A and create an item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Alice")
    page.fill('input[name="email"]', user_a_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_a_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    alice_item = f"Alice Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', alice_item)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Register User B and create an item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Bob")
    page.fill('input[name="email"]', user_b_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_b_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    bob_item = f"Bob Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', bob_item)
    page.click('button[type="submit"]')

    # Go to items list
    page.goto(f"{live_server}/items")

    # Both items should be visible initially
    expect(page.locator(f'text="{alice_item}"')).to_be_visible()
    expect(page.locator(f'text="{bob_item}"')).to_be_visible()

    # Filter by Alice (User A) - select from dropdown
    user_filter = page.locator('select[name="user_filter"]')
    user_filter.select_option(label="Alice")
    page.click('button:has-text("Apply")')

    # Only Alice's item should be visible
    expect(page.locator(f'text="{alice_item}"')).to_be_visible()
    expect(page.locator(f'text="{bob_item}"')).not_to_be_visible()


def test_filter_items_by_status(page, live_server):
    """Test filtering items by status."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"
    claimer_email = f"claimer+{uuid.uuid4().hex[:8]}@example.com"

    # Register owner and create item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Owner")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    available_item = f"Available Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', available_item)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    claimed_item = f"Claimed Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', claimed_item)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Register claimer and claim one item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Claimer")
    page.fill('input[name="email"]', claimer_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', claimer_email)
    page.click('button[type="submit"]')

    # Claim the second item from dashboard
    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{claimed_item}")')
    claim_button = item_card.locator('button.btn-outline-primary:has-text("Claim")')
    claim_button.click()

    # Wait for HTMX update
    page.wait_for_timeout(500)

    # Go to items list and filter by Available status
    page.goto(f"{live_server}/items")
    status_filter = page.locator('select[name="status_filter"]')
    status_filter.select_option("Available")
    page.click('button:has-text("Apply")')

    # Only the available item should be visible
    expect(page.locator(f'text="{available_item}"')).to_be_visible()
    expect(page.locator(f'text="{claimed_item}"')).not_to_be_visible()


def test_search_items(page, live_server):
    """Test searching items by text."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Searcher")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Create items with distinct descriptions
    page.goto(f"{live_server}/submit_item")
    unique_id = uuid.uuid4().hex[:8]
    searchable_item = f"UNIQUESEARCH{unique_id}"
    page.fill('input[name="description"]', searchable_item)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    other_item = f"Other Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', other_item)
    page.click('button[type="submit"]')

    # Go to items and search
    page.goto(f"{live_server}/items")
    search_input = page.locator('input[name="q"]')
    search_input.fill(f"UNIQUESEARCH{unique_id}")
    page.click('button:has-text("Apply")')

    # Only the searched item should be visible
    expect(page.locator(f'text="{searchable_item}"')).to_be_visible()
    expect(page.locator(f'text="{other_item}"')).not_to_be_visible()


def test_clear_filters(page, live_server):
    """Test clearing all filters."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Filter Clearer")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Create two items
    page.goto(f"{live_server}/submit_item")
    item1 = f"Item One {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item1)
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    item2 = f"Item Two {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', item2)
    page.click('button[type="submit"]')

    # Go to items and apply a search filter
    page.goto(f"{live_server}/items")
    search_input = page.locator('input[name="q"]')
    search_input.fill("One")
    page.click('button:has-text("Apply")')

    # Only item1 should be visible
    expect(page.locator(f'text="{item1}"')).to_be_visible()
    expect(page.locator(f'text="{item2}"')).not_to_be_visible()

    # Clear filters - text is "Clear all filters"
    page.click('a:has-text("Clear all filters")')

    # Both items should be visible again
    expect(page.locator(f'text="{item1}"')).to_be_visible()
    expect(page.locator(f'text="{item2}"')).to_be_visible()


def test_sort_items_by_price(page, live_server):
    """Test sorting items by price."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Sorter")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Create items with different prices
    page.goto(f"{live_server}/submit_item")
    cheap_item = f"Cheap Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', cheap_item)
    page.fill('input[name="price"]', "10.00")
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    expensive_item = f"Expensive Item {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', expensive_item)
    page.fill('input[name="price"]', "100.00")
    page.click('button[type="submit"]')

    # Go to items and sort by price ascending
    page.goto(f"{live_server}/items")
    sort_by = page.locator('select[name="sort_by"]')
    sort_by.select_option("price")
    sort_order = page.locator('select[name="sort_order"]')
    sort_order.select_option("asc")
    page.click('button:has-text("Apply")')

    # Verify both items are visible (sorting doesn't filter)
    expect(page.locator(f'text="{cheap_item}"')).to_be_visible()
    expect(page.locator(f'text="{expensive_item}"')).to_be_visible()


def test_filter_by_priority(page, live_server):
    """Test filtering items by priority."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Priority User")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Create high priority item
    page.goto(f"{live_server}/submit_item")
    high_priority_item = f"High Priority {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', high_priority_item)
    page.select_option('select[name="priority"]', "High")
    page.click('button[type="submit"]')

    # Create low priority item
    page.goto(f"{live_server}/submit_item")
    low_priority_item = f"Low Priority {uuid.uuid4().hex[:8]}"
    page.fill('input[name="description"]', low_priority_item)
    page.select_option('select[name="priority"]', "Low")
    page.click('button[type="submit"]')

    # Filter by High priority
    page.goto(f"{live_server}/items")
    priority_filter = page.locator('select[name="priority_filter"]')
    priority_filter.select_option("High")
    page.click('button:has-text("Apply")')

    # Only high priority should be visible
    expect(page.locator(f'text="{high_priority_item}"')).to_be_visible()
    expect(page.locator(f'text="{low_priority_item}"')).not_to_be_visible()
