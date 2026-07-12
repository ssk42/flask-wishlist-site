"""Browser tests for critical path robustness (validation, recovery, state consistency)."""
import uuid
import re
from playwright.sync_api import expect


def test_critical_wishlist_flow(page, live_server):
    """Test the complete wishlist flow including validation errors, recovery, and state consistency."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"
    item_desc_1 = f"Critical Item 1 {uuid.uuid4().hex[:8]}"
    item_desc_2 = f"Critical Item 2 {uuid.uuid4().hex[:8]}"

    # 1. Setup User
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Critical Tester")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # 2. Create Item with Invalid Data -> Recover
    page.goto(f"{live_server}/submit_item")
    # Leave description empty to trigger HTML5 validation first
    page.fill('input[name="description"]', "")
    
    # Attempt to bypass HTML5 validation to hit server validation
    page.evaluate('document.querySelector("input[name=description]").removeAttribute("required")')
    
    # Send a negative price to trigger server-side validation
    page.evaluate('document.querySelector("input[name=price]").removeAttribute("min")')
    page.fill('input[name="price"]', "-10")
    page.click('button[type="submit"]')
    
    # Verify server validation error - we expect 'Description cannot be empty' but form_validators says 'Description is required'
    # Wait, the error is 'A description is required to create an item.' in items.py
    expect(page.locator('.alert-danger').first).to_be_visible()
    
    # Recover and submit valid
    page.fill('input[name="description"]', item_desc_1)
    page.fill('input[name="price"]', "10.00")
    page.select_option('select[name="priority"]', "High")
    page.click('button[type="submit"]')
    expect(page.locator('.alert-success')).to_contain_text("added")
    
    # 3. Double-Submit Prevention
    # Navigate back to the form manually
    page.goto(f"{live_server}/submit_item")
    page.fill('input[name="description"]', item_desc_2)
    page.select_option('select[name="priority"]', "Medium")
    page.click('button[type="submit"]')
    
    # 4. Verify Ordering (Priority then Description)
    page.goto(f"{live_server}/items")
    # High priority should be before Medium priority
    # Find all descriptions
    cards = page.locator('.glass-card h3').all_text_contents()
    # Filter our items
    our_items = [t for t in cards if "Critical Item" in t]
    assert our_items[0] == item_desc_1  # High priority
    assert our_items[1] == item_desc_2  # Medium priority

    # 5. Edit Item with Invalid Data -> Recover
    item_card = page.locator(f'.glass-card:has-text("{item_desc_1}")')
    item_card.locator('a:has-text("Edit")').click()
    
    # Trigger server validation error on priority
    # Modify DOM to submit invalid priority
    page.evaluate('''
        const select = document.querySelector("select[name=priority]");
        const opt = document.createElement("option");
        opt.value = "Invalid";
        opt.text = "Invalid";
        select.appendChild(opt);
    ''')
    page.select_option('select[name="priority"]', "Invalid")
    page.click('button[type="submit"]')
    
    # Should see the new error message we added
    expect(page.locator('.alert-danger')).to_contain_text("choose a valid priority", ignore_case=True)
    
    # Recover and submit valid
    page.select_option('select[name="priority"]', "Low")
    page.click('button[type="submit"]')
    expect(page.locator('.alert-success')).to_contain_text("updated successfully")

    # 6. Verify Sorting changed due to edit
    page.goto(f"{live_server}/items")
    cards = page.locator('.glass-card h3').all_text_contents()
    our_items = [t for t in cards if "Critical Item" in t]
    assert our_items[0] == item_desc_2  # Medium priority (was 2)
    assert our_items[1] == item_desc_1  # Low priority (was 1)

    # 7. Delete Consistency
    item_card_to_delete = page.locator(f'.glass-card:has-text("{item_desc_2}")')
    
    # Grab the delete form action URL so we can manually hit it later
    delete_form_action = item_card_to_delete.locator('form').get_attribute('action')
    
    page.on("dialog", lambda dialog: dialog.accept())
    item_card_to_delete.locator('button:has-text("Delete")').click()
    expect(page.locator('.alert-info')).to_contain_text("deleted")
    expect(page.locator(f'.glass-card:has-text("{item_desc_2}")')).not_to_be_visible()

    # 8. Simulate hitting delete again (e.g. stale state / duplicate request)
    # Safer way: grab csrf token from another item's delete button (we still have item_desc_1)
    csrf_token = page.locator('input[name="csrf_token"]').first.get_attribute('value')
    
    page.evaluate(f'''(data) => {{
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = data.url;
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrf_token';
        input.value = data.csrf;
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    }}''', {"url": delete_form_action, "csrf": csrf_token})
    
    # Now wait for the page to load and check the flash message
    page.wait_for_load_state('networkidle')
    # Should hit the "Item not found or already deleted" condition
    expect(page.locator('.alert-warning')).to_contain_text("not found or already deleted", ignore_case=True)
