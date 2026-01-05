"""Browser tests for Price History UI."""
import uuid
from playwright.sync_api import expect
from models import Item, PriceHistory, User, db


def test_price_history_sparkline_visibility(page, live_server, browser_app):
    """Test that sparkline graph is visible for items with price history."""
    owner_email = f"history_owner_{uuid.uuid4().hex[:8]}@example.com"
    viewer_email = f"history_viewer_{uuid.uuid4().hex[:8]}@example.com"

    # Create users and item directly in DB
    item_desc = f"History Item {uuid.uuid4().hex[:8]}"
    
    with browser_app.app_context():
        db.session.remove()
        
        # Create Owner
        owner = User(name="History Owner", email=owner_email, is_private=False)
        db.session.add(owner)
        db.session.commit()
        
        # Create Item with price
        item = Item(description=item_desc, user_id=owner.id, price=100.0)
        db.session.add(item)
        db.session.commit()
        
        # Add Price History (Need at least 2 points for sparkline to render)
        h1 = PriceHistory(item_id=item.id, price=120.0, source='initial')
        h2 = PriceHistory(item_id=item.id, price=100.0, source='auto')
        db.session.add_all([h1, h2])
        
        # Create Viewer
        viewer = User(name="History Viewer", email=viewer_email, is_private=False)
        db.session.add(viewer)
        
        db.session.commit()

    # Login as viewer
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', viewer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.get_by_role("button", name="Log in").click()
    
    # Verify login succeeded
    expect(page).to_have_url(f"{live_server}/")
    expect(page.locator('a[href="/logout"]')).to_be_visible()
    
    # Navigate to All Items page (sparkline is in _item_card.html)
    page.goto(f"{live_server}/items")

    # Verify Item Card is visible
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    item_card.wait_for(state="visible", timeout=5000)
    expect(item_card).to_be_visible()
    
    # Verify Sparkline Container becomes visible (JS fetched data and displayed it)
    sparkline = item_card.locator('.price-sparkline')
    expect(sparkline).to_be_visible(timeout=5000)
    
    # Verify canvas exists inside
    expect(sparkline.locator('canvas')).to_be_visible()

    # Verify title attribute contains price range info
    for _ in range(10):
        if sparkline.get_attribute("title"):
             break
        page.wait_for_timeout(200)

    title = sparkline.get_attribute("title")
    assert title is not None, "Sparkline title attribute should be set"
    assert "Price range" in title, f"Title should contain 'Price range', got: {title}"
