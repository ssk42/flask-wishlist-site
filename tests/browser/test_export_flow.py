"""Browser tests for Export functionality (CSV exports)."""
import uuid
from playwright.sync_api import expect


def test_export_items_link_visible(page, live_server):
    """Test export items link is visible on items page."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Export User")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Create an item first
    page.goto(f"{live_server}/submit_item")
    page.fill('input[name="description"]', f"Export Item {uuid.uuid4().hex[:8]}")
    page.click('button[type="submit"]')

    # Go to items page
    page.goto(f"{live_server}/items")
    export_link = page.locator('a:has-text("Export my updates")')
    expect(export_link).to_be_visible()


def test_export_items_downloads_csv(page, live_server):
    """Test export_items returns an Excel file with correct content."""
    import pandas as pd
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"
    user_name = "CSV User"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', user_name)
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Create items with known data
    item1_desc = f"CSV Item 1 {uuid.uuid4().hex[:8]}"
    item2_desc = f"CSV Item 2 {uuid.uuid4().hex[:8]}"
    
    page.goto(f"{live_server}/submit_item")
    page.fill('input[name="description"]', item1_desc)
    page.fill('input[name="price"]', "25.00")
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/submit_item")
    page.fill('input[name="description"]', item2_desc)
    page.fill('input[name="price"]', "50.00")
    page.click('button[type="submit"]')

    # Navigate to any page first, then trigger download via location change
    page.goto(f"{live_server}/items")
    with page.expect_download() as download_info:
        # Trigger download by navigating to the export URL
        page.evaluate("window.location.href = '/export_items';")

    download = download_info.value
    # Verify it's an Excel file
    assert download.suggested_filename.endswith('.xlsx')
    
    # Wait for download to complete and get the file path
    download_path = download.path()
    
    # Read the Excel content using pandas (same library that wrote it)
    df = pd.read_excel(download_path)
    
    # Verify headers exist
    assert 'User' in df.columns, f"Expected 'User' column, got: {list(df.columns)}"
    assert 'Description' in df.columns, f"Expected 'Description' column, got: {list(df.columns)}"
    assert 'Price' in df.columns, f"Expected 'Price' column, got: {list(df.columns)}"
    
    # Verify our created items appear in the export
    descriptions = df['Description'].tolist()
    assert item1_desc in descriptions, f"Expected '{item1_desc}' in {descriptions}"
    assert item2_desc in descriptions, f"Expected '{item2_desc}' in {descriptions}"
    
    # Verify prices match
    for _, row in df.iterrows():
        if row['Description'] == item1_desc:
            assert row['Price'] == 25.0, f"Expected 25.00, got {row['Price']}"
        elif row['Description'] == item2_desc:
            assert row['Price'] == 50.0, f"Expected 50.00, got {row['Price']}"


def test_export_my_status_updates_link_visible(page, live_server):
    """Test export status updates link is visible on items page."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Status User")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    # Export link is on items page, not my-claims
    page.goto(f"{live_server}/items")
    export_link = page.locator('a:has-text("Export my updates")')
    expect(export_link).to_be_visible()


def test_export_my_status_updates_downloads_csv(page, live_server):
    """Test export status updates returns an Excel file with correct content."""
    owner_email = f"owner+{uuid.uuid4().hex[:8]}@example.com"
    claimer_email = f"claimer+{uuid.uuid4().hex[:8]}@example.com"
    item_desc = f"Claimable {uuid.uuid4().hex[:8]}"

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
    page.fill('input[name="description"]', item_desc)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Claimer claims item
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Claimer")
    page.fill('input[name="email"]', claimer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', claimer_email)
    page.fill('input[name="password"]', 'testsecret')
    page.click('button[type="submit"]')

    page.goto(f"{live_server}/")
    item_card = page.locator(f'.glass-card:has-text("{item_desc}")')
    item_card.locator('button:has-text("Claim")').click()
    page.wait_for_timeout(500)

    # Navigate to items page and click export link (export is on items page)
    page.goto(f"{live_server}/items")
    with page.expect_download() as download_info:
        page.locator('a:has-text("Export my updates")').click()

    download = download_info.value
    # Actual exports are Excel files
    assert download.suggested_filename.endswith('.xlsx')
    
    # Read the Excel content using pandas
    import pandas as pd
    download_path = download.path()
    df = pd.read_excel(download_path)
    
    # Verify headers exist
    assert 'Description' in df.columns, f"Expected 'Description' column, got: {list(df.columns)}"
    assert 'Status' in df.columns, f"Expected 'Status' column, got: {list(df.columns)}"
    
    # Verify the claimed item appears in the export
    descriptions = df['Description'].tolist()
    assert item_desc in descriptions, f"Expected '{item_desc}' in {descriptions}"
    
    # Verify the item has a status set
    for _, row in df.iterrows():
        if row['Description'] == item_desc:
            # Status should be set for claimed items
            assert pd.notna(row['Status']), "Status should not be NaN for claimed item"


def test_export_requires_login(page, live_server):
    """Test export_my_status_updates endpoint requires login (export_items does not require login)."""
    # export_my_status_updates requires login - should redirect to login
    response = page.goto(f"{live_server}/export_my_status_updates")
    page.wait_for_load_state('networkidle')
    assert "/login" in page.url
