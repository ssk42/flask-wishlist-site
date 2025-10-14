import uuid

from playwright.sync_api import expect


def test_registration_flow(page, live_server):
    unique_email = f"browser+{uuid.uuid4().hex[:8]}@example.com"

    page.goto(f"{live_server}/register")
    expect(page).to_have_title("Register · Wishlist App")

    page.fill('input[name="name"]', "Browser Tester")
    page.fill('input[name="email"]', unique_email)
    page.click('button[type="submit"]')

    expect(page).to_have_url(f"{live_server}/login")
    alert = page.locator('.alert-success')
    expect(alert).to_contain_text("Registration successful")
    expect(page.locator('form input[name="email"]')).to_be_visible()
