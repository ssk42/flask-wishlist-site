from playwright.sync_api import Page, expect


def test_split_gift_flow(page: Page, live_server, browser_app):
    """Test the complete flow of splitting a gift."""

    # 1. Setup: Create users and item
    with browser_app.app_context():
        from models import db, User, Item

        # Owner
        owner = User(name="Owner", email="owner@example.com")
        db.session.add(owner)
        db.session.commit()

        # Splitter (Organizer)
        splitter = User(name="Splitter", email="splitter@example.com")
        db.session.add(splitter)
        db.session.commit()

        # Contributor
        contributor = User(name="Contributor", email="contributor@example.com")
        db.session.add(contributor)
        db.session.commit()

        # Item
        item = Item(
            description="Expensive Gift",
            price=100.0,
            user_id=owner.id,
            status="Available"
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # 2. Splitter starts the split
    # Login
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', 'splitter@example.com')
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    # Navigate to Items List where full actions are available
    page.goto(f"{live_server}/items")
    # Scope to the specific card to avoid strict mode violations (modals also
    # contain text)
    item_card = page.locator(f'#item-card-{item_id}')
    expect(item_card.get_by_text("Expensive Gift")).to_be_visible()

    # Start split
    # Check claim button first to ensure actions are visible
    expect(item_card.get_by_role("button", name="Claim")).to_be_visible()

    # Click Split button using CSS selector to be precise
    # Ensure no stale backdrops
    expect(page.locator(".modal-backdrop")).not_to_be_visible()

    split_btn = item_card.locator("button[data-bs-target*='#splitModal']")
    expect(split_btn).to_be_visible()
    split_btn.click()

    expect(page.get_by_text("Start a group gift")).to_be_visible()
    page.fill(f'#startAmount{item_id}', '25')
    page.click('button:has-text("Start Split")')

    # Verify split started
    expect(page.get_by_text("You started a split")).to_be_visible()
    expect(page.get_by_text("🤝 SPLITTING")).to_be_visible()
    expect(page.get_by_text("25% funded")).to_be_visible()

    page.click('a:has-text("Logout")')

    # 3. Contributor joins the split
    # Login
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', 'contributor@example.com')
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Ensure we are on the items page
    page.goto(f"{live_server}/items")

    # Verify "Join Split" button is visible
    join_btn = item_card.locator("button[data-bs-target*='#splitModal']")
    expect(join_btn).to_be_visible()
    expect(join_btn).to_have_text("Join Split")

    # Ensure no backdrops from previous interactions
    expect(page.locator(".modal-backdrop")).not_to_be_visible()

    # Join split
    join_btn.click()
    expect(page.get_by_text("Join Split Gift")).to_be_visible()
    page.fill(f'#contributionAmount{item_id}', '25')
    page.click('#splitModal button:has-text("Join Split")')

    # Verify contribution
    expect(page.get_by_text("You contributed $25.00")).to_be_visible()
    expect(page.get_by_text("50% funded")).to_be_visible()

    page.click('a:has-text("Logout")')

    # 4. Owner should see "Available" (Surprise Protection)
    # Login
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', 'owner@example.com')
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Ensure we are on the items page to see the item card
    page.goto(f"{live_server}/items")

    # Verify owner view
    expect(page.get_by_text("Expensive Gift")).to_be_visible()
    expect(item_card.get_by_text("Your Item")).to_be_visible()
    # Surprise protection verification
    expect(item_card.get_by_text("Splitting")).not_to_be_visible()
