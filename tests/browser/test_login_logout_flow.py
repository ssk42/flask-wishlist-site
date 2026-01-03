"""Browser tests for Login and Logout functionality."""
import uuid
from playwright.sync_api import expect


def test_login_page_renders(page, live_server):
    """Test that login page renders correctly."""
    page.goto(f"{live_server}/login")
    expect(page.locator('h1:has-text("Welcome back")')).to_be_visible()
    expect(page.locator('input[name="email"]')).to_be_visible()
    expect(page.locator('button[type="submit"]')).to_be_visible()


def test_login_with_valid_email(page, live_server):
    """Test successful login with registered email."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"
    user_name = f"TestUser{uuid.uuid4().hex[:4]}"

    # Register first
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', user_name)
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # After registration, we're on login page - go to logout to clear session
    page.goto(f"{live_server}/logout")

    # Login
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Should redirect to dashboard and show welcome message with user name
    expect(page).to_have_url(f"{live_server}/")
    # Use first() to handle multiple matches (e.g., in both flash message and header)
    expect(page.locator(f'text="Welcome back, {user_name}!"').first).to_be_visible()


def test_login_with_invalid_email(page, live_server):
    """Test login with unregistered email shows error."""
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', "nonexistent@example.com")
    page.click('button[type="submit"]')

    # Should show error message
    expect(page.locator('.alert-danger')).to_contain_text("could not find an account")


def test_login_redirects_to_next_url(page, live_server):
    """Test login redirects to requested page after auth."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"

    # Register
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', "Redirect User")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Try to access protected page
    page.goto(f"{live_server}/events")

    # Should redirect to login with next parameter
    expect(page).to_have_url(f"{live_server}/login?next=%2Fevents")

    # Login
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Wait for navigation to complete and verify redirect to events page
    page.wait_for_load_state('networkidle')
    assert "/events" in page.url


def test_logout_flow(page, live_server):
    """Test logout clears session and redirects."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"
    user_name = f"LogoutUser{uuid.uuid4().hex[:4]}"

    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', user_name)
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/login")
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')

    # Verify logged in by checking the welcome message
    page.goto(f"{live_server}/")
    expect(page.locator(f'text="Welcome back, {user_name}!"').first).to_be_visible()

    # Logout
    page.goto(f"{live_server}/logout")

    # Should redirect to home and show login link (use sidebar-link class and first to avoid strict mode)
    expect(page.locator('.sidebar-link:has-text("Login")').first).to_be_visible()


def test_forgot_email_page_renders(page, live_server):
    """Test forgot email page renders."""
    page.goto(f"{live_server}/forgot_email")
    expect(page.locator('h1:has-text("Forgot your email")')).to_be_visible()


def test_forgot_email_with_valid_name(page, live_server):
    """Test forgot email finds user by name."""
    user_email = f"user+{uuid.uuid4().hex[:8]}@example.com"
    unique_name = f"UniqueName{uuid.uuid4().hex[:8]}"

    # Register
    page.goto(f"{live_server}/register")
    page.fill('input[name="name"]', unique_name)
    page.fill('input[name="email"]', user_email)
    page.click('button[type="submit"]')
    page.goto(f"{live_server}/logout")

    # Forgot email
    page.goto(f"{live_server}/forgot_email")
    page.fill('input[name="name"]', unique_name)
    page.click('button[type="submit"]')

    # Should show success message with email
    expect(page.locator('.alert-success')).to_be_visible()


def test_forgot_email_with_invalid_name(page, live_server):
    """Test forgot email with unknown name shows error."""
    page.goto(f"{live_server}/forgot_email")
    page.fill('input[name="name"]', "NonexistentUser12345")
    page.click('button[type="submit"]')

    # Should show error
    expect(page.locator('.alert-danger')).to_contain_text("could not find an account with that name")
