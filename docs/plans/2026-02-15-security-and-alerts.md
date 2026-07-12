# Security Hardening + Price Drop Alerts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix critical security vulnerabilities (DELETE CSRF, SSRF, XSS) and add price drop notifications

**Architecture:** Security fixes add validation layers to existing routes; price alerts extend existing Celery task to check PriceHistory and create Notifications

**Tech Stack:** Flask, SQLAlchemy, Celery, pytest, Playwright

---

## Phase 0: Security Hardening (Critical)

### Task 1: Fix DELETE via GET (CSRF Bypass)

**Files:**
- Modify: `blueprints/items.py:413` (delete_item route)
- Modify: `templates/partials/_item_card.html` (delete button)
- Test: `tests/unit/test_security.py` (new file)

**Step 1: Write failing security test**

Create `tests/unit/test_security.py`:

```python
import pytest
from flask import url_for

def test_delete_item_rejects_get_requests(client, login, user):
    """DELETE via GET should return 405 Method Not Allowed."""
    from models import Item, db

    item = Item(
        description="Test Item",
        user_id=user.id,
        status="Available"
    )
    db.session.add(item)
    db.session.commit()

    # Attempt GET request (CSRF bypass vector)
    response = client.get(f'/delete_item/{item.id}')

    # Should reject GET requests
    assert response.status_code == 405

    # Item should still exist
    assert Item.query.get(item.id) is not None

def test_delete_item_requires_csrf_token(client, login, user):
    """DELETE via POST without CSRF should return 400."""
    from models import Item, db

    item = Item(
        description="Test Item",
        user_id=user.id,
        status="Available"
    )
    db.session.add(item)
    db.session.commit()

    # POST without CSRF token
    response = client.post(f'/delete_item/{item.id}')

    # Should reject due to missing CSRF
    assert response.status_code == 400

def test_delete_item_succeeds_with_valid_post(client, login, user):
    """DELETE via POST with CSRF should succeed."""
    from models import Item, db

    item = Item(
        description="Test Item",
        user_id=user.id,
        status="Available"
    )
    db.session.add(item)
    db.session.commit()
    item_id = item.id

    # POST with CSRF token (Flask test client handles this automatically)
    response = client.post(
        f'/delete_item/{item_id}',
        follow_redirects=True
    )

    # Should succeed
    assert response.status_code == 200

    # Item should be deleted
    assert Item.query.get(item_id) is None
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_security.py::test_delete_item_rejects_get_requests -v
```

Expected: FAIL (currently allows GET)

**Step 3: Update delete_item route to require POST**

In `blueprints/items.py`, find the `delete_item` function (around line 413) and change:

```python
@bp.route('/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    """Delete an item (POST only for CSRF protection)."""
    item = db.session.get(Item, item_id)

    if not item:
        flash('Item not found', 'error')
        return redirect(url_for('items.items_list'))

    if item.user_id != current_user.id:
        flash('You can only delete your own items', 'error')
        return redirect(url_for('items.items_list'))

    db.session.delete(item)
    db.session.commit()

    flash(f'Item "{item.description}" has been deleted', 'success')
    return redirect(url_for('items.items_list'))
```

**Step 4: Update template to use POST form**

In `templates/partials/_item_card.html`, find the delete link and replace with:

```html
<!-- Find this: -->
<a href="{{ url_for('items.delete_item', item_id=item.id) }}" class="...">Delete</a>

<!-- Replace with: -->
<form method="POST" action="{{ url_for('items.delete_item', item_id=item.id) }}" style="display:inline;">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
  <button type="submit" class="btn btn-sm btn-danger" onclick="return confirm('Are you sure you want to delete this item?')">
    Delete
  </button>
</form>
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_security.py -v
```

Expected: PASS (all 3 tests)

**Step 6: Commit**

```bash
git add blueprints/items.py templates/partials/_item_card.html tests/unit/test_security.py
git commit -m "security: fix DELETE-via-GET CSRF bypass

- Require POST method for delete_item route
- Update template to use form with CSRF token
- Add security tests for GET rejection and CSRF validation"
```

---

### Task 2: Add SSRF Protection to Price Service

**Files:**
- Modify: `services/price_service.py` (add URL validation)
- Modify: `blueprints/api.py:9` (fetch-metadata endpoint)
- Modify: `blueprints/items.py:384` (refresh-price endpoint)
- Test: `tests/unit/test_security.py` (add SSRF tests)

**Step 1: Write failing SSRF tests**

Add to `tests/unit/test_security.py`:

```python
def test_ssrf_blocks_private_ips():
    """URL validation should reject private IP ranges."""
    from services.price_service import validate_url

    # Localhost
    assert validate_url('http://127.0.0.1/') == False
    assert validate_url('http://localhost/') == False

    # Private networks
    assert validate_url('http://10.0.0.1/') == False
    assert validate_url('http://192.168.1.1/') == False
    assert validate_url('http://172.16.0.1/') == False

    # AWS metadata (link-local)
    assert validate_url('http://169.254.169.254/latest/meta-data/') == False

def test_ssrf_blocks_non_http_schemes():
    """URL validation should only allow http/https."""
    from services.price_service import validate_url

    assert validate_url('file:///etc/passwd') == False
    assert validate_url('ftp://example.com/') == False
    assert validate_url('gopher://example.com/') == False
    assert validate_url('data:text/html,<script>alert(1)</script>') == False

def test_ssrf_allows_valid_urls():
    """URL validation should allow legitimate URLs."""
    from services.price_service import validate_url

    assert validate_url('https://www.amazon.com/product') == True
    assert validate_url('http://www.target.com/item') == True
    assert validate_url('https://example.com/page') == True

def test_fetch_metadata_rejects_ssrf(client, login):
    """API endpoint should reject SSRF attempts."""
    response = client.post(
        '/api/fetch-metadata',
        json={'url': 'http://169.254.169.254/latest/meta-data/'}
    )

    assert response.status_code == 400
    data = response.get_json()
    assert 'Invalid or unsafe URL' in data.get('error', '')
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_security.py::test_ssrf_blocks_private_ips -v
```

Expected: FAIL (validate_url function doesn't exist yet)

**Step 3: Implement URL validation in price_service**

In `services/price_service.py`, add at the top (after imports):

```python
from urllib.parse import urlparse
import ipaddress
import socket

PRIVATE_IP_RANGES = [
    ipaddress.ip_network('127.0.0.0/8'),    # localhost
    ipaddress.ip_network('10.0.0.0/8'),     # private
    ipaddress.ip_network('172.16.0.0/12'),  # private
    ipaddress.ip_network('192.168.0.0/16'), # private
    ipaddress.ip_network('169.254.0.0/16'), # link-local (AWS metadata)
]

def validate_url(url: str) -> bool:
    """Validate URL is safe for server-side fetch (SSRF protection).

    Args:
        url: URL to validate

    Returns:
        True if URL is safe, False otherwise
    """
    try:
        parsed = urlparse(url)

        # Only allow http/https
        if parsed.scheme not in ['http', 'https']:
            return False

        # Require hostname
        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve hostname to IP and check against private ranges
        ip_str = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip_str)

        for network in PRIVATE_IP_RANGES:
            if ip_obj in network:
                return False

        return True
    except Exception:
        # Any error in parsing/resolution = unsafe
        return False
```

**Step 4: Update _make_request to validate URLs**

In `services/price_service.py`, find `_make_request` function and add validation:

```python
def _make_request(url: str, retries: int = 3):
    """Make HTTP request with retry logic and SSRF protection."""

    # SSRF protection
    if not validate_url(url):
        raise ValueError(f"Invalid or unsafe URL: {url}")

    # ... rest of existing logic
```

**Step 5: Update API endpoint to handle validation errors**

In `blueprints/api.py`, update `/api/fetch-metadata` route:

```python
@bp.route('/api/fetch-metadata', methods=['POST'])
@login_required
def fetch_metadata():
    """Fetch product metadata from URL."""
    from services.price_service import fetch_price, validate_url

    data = request.get_json()
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'error': 'URL required'}), 400

    # SSRF protection
    if not validate_url(url):
        return jsonify({'error': 'Invalid or unsafe URL'}), 400

    try:
        price = fetch_price(url)
        return jsonify({
            'price': price,
            'url': url
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

**Step 6: Update refresh-price endpoint**

In `blueprints/items.py`, find `refresh_price` route (around line 384) and add validation:

```python
@bp.route('/item/<int:item_id>/refresh-price', methods=['POST'])
@login_required
def refresh_price(item_id):
    """Manually refresh price for an item."""
    from services.price_service import fetch_price, validate_url

    item = db.session.get(Item, item_id)

    if not item:
        return jsonify({'error': 'Item not found'}), 404

    if not item.link:
        return jsonify({'error': 'No link to fetch from'}), 400

    # SSRF protection
    if not validate_url(item.link):
        return jsonify({'error': 'Invalid or unsafe URL'}), 400

    try:
        new_price = fetch_price(item.link)

        if new_price:
            item.price = new_price
            item.price_last_checked = datetime.datetime.now(datetime.timezone.utc)
            db.session.commit()

            return jsonify({
                'success': True,
                'price': new_price
            })
        else:
            return jsonify({'error': 'Could not fetch price'}), 500

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Price fetch failed'}), 500
```

**Step 7: Run tests to verify they pass**

```bash
pytest tests/unit/test_security.py::test_ssrf -v
```

Expected: PASS (all SSRF tests)

**Step 8: Commit**

```bash
git add services/price_service.py blueprints/api.py blueprints/items.py tests/unit/test_security.py
git commit -m "security: add SSRF protection to price fetching

- Add validate_url() with private IP and scheme checks
- Block localhost, private networks, link-local (AWS metadata)
- Update fetch-metadata and refresh-price endpoints
- Add comprehensive SSRF tests"
```

---

### Task 3: Add URL Scheme Validation (XSS Prevention)

**Files:**
- Create: `services/form_validators.py`
- Modify: `blueprints/items.py` (submit/edit routes)
- Test: `tests/unit/test_form_validators.py` (new file)

**Step 1: Write failing XSS tests**

Create `tests/unit/test_form_validators.py`:

```python
import pytest

def test_url_scheme_validation_blocks_javascript():
    """Should reject javascript: URLs (XSS vector)."""
    from services.form_validators import validate_url_scheme

    assert validate_url_scheme('javascript:alert(1)') == False
    assert validate_url_scheme('javascript:void(0)') == False

def test_url_scheme_validation_blocks_data_urls():
    """Should reject data: URLs."""
    from services.form_validators import validate_url_scheme

    assert validate_url_scheme('data:text/html,<script>alert(1)</script>') == False

def test_url_scheme_validation_allows_http():
    """Should allow http and https URLs."""
    from services.form_validators import validate_url_scheme

    assert validate_url_scheme('https://www.amazon.com/product') == True
    assert validate_url_scheme('http://www.target.com/item') == True

def test_url_scheme_validation_allows_empty():
    """Empty URLs should be allowed (optional field)."""
    from services.form_validators import validate_url_scheme

    assert validate_url_scheme('') == True
    assert validate_url_scheme(None) == True

def test_submit_item_rejects_javascript_link(client, login, user):
    """Submitting item with javascript: link should fail."""
    response = client.post('/submit_item', data={
        'description': 'Test Item',
        'link': 'javascript:alert(document.cookie)',
        'csrf_token': 'valid'  # Test client auto-handles CSRF
    }, follow_redirects=True)

    # Should show error message
    assert b'must be a valid http or https URL' in response.data

    # Item should not be created
    from models import Item
    assert Item.query.filter_by(description='Test Item').first() is None
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_form_validators.py::test_url_scheme_validation_blocks_javascript -v
```

Expected: FAIL (validate_url_scheme doesn't exist)

**Step 3: Create form validators module**

Create `services/form_validators.py`:

```python
"""Form validation utilities for security and data integrity."""

from urllib.parse import urlparse

def validate_url_scheme(url: str) -> bool:
    """Validate URL uses http or https scheme (XSS prevention).

    Prevents javascript:, data:, file:, and other non-HTTP schemes
    that could be used for XSS attacks when rendered in <a href>.

    Args:
        url: URL to validate (can be None or empty for optional fields)

    Returns:
        True if URL is safe or empty, False otherwise
    """
    # Allow empty/None (optional field)
    if not url:
        return True

    try:
        parsed = urlparse(url.strip())

        # Allow http, https, or empty scheme (relative URLs)
        return parsed.scheme in ['http', 'https', '']
    except Exception:
        return False
```

**Step 4: Update submit_item route with validation**

In `blueprints/items.py`, find `submit_item` route and add validation:

```python
@bp.route('/submit_item', methods=['GET', 'POST'])
@login_required
def submit_item():
    """Submit a new wishlist item."""
    from services.form_validators import validate_url_scheme

    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        link = request.form.get('link', '').strip()
        image_url = request.form.get('image_url', '').strip()
        # ... other fields

        # Validation
        if not description:
            flash('Description is required', 'error')
            return redirect(url_for('items.submit_item'))

        # URL scheme validation (XSS prevention)
        if link and not validate_url_scheme(link):
            flash('Link must be a valid http or https URL', 'error')
            return redirect(url_for('items.submit_item'))

        if image_url and not validate_url_scheme(image_url):
            flash('Image URL must be a valid http or https URL', 'error')
            return redirect(url_for('items.submit_item'))

        # ... rest of existing logic
```

**Step 5: Update edit_item route with validation**

In `blueprints/items.py`, find `edit_item` route and add same validation:

```python
@bp.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Edit an existing item."""
    from services.form_validators import validate_url_scheme

    item = db.session.get(Item, item_id)
    # ... existing checks

    if request.method == 'POST':
        link = request.form.get('link', '').strip()
        image_url = request.form.get('image_url', '').strip()

        # URL scheme validation (XSS prevention)
        if link and not validate_url_scheme(link):
            flash('Link must be a valid http or https URL', 'error')
            return redirect(url_for('items.edit_item', item_id=item_id))

        if image_url and not validate_url_scheme(image_url):
            flash('Image URL must be a valid http or https URL', 'error')
            return redirect(url_for('items.edit_item', item_id=item_id))

        # ... rest of existing logic
```

**Step 6: Run tests to verify they pass**

```bash
pytest tests/unit/test_form_validators.py -v
```

Expected: PASS (all tests)

**Step 7: Commit**

```bash
git add services/form_validators.py blueprints/items.py tests/unit/test_form_validators.py
git commit -m "security: add URL scheme validation (XSS prevention)

- Create form_validators module with validate_url_scheme()
- Block javascript:, data:, and other non-HTTP schemes
- Apply validation to submit_item and edit_item routes
- Add comprehensive form validation tests"
```

---

## Phase 1: Price Drop Alerts

### Task 4: Add Price Drop Detection to Update Task

**Files:**
- Modify: `services/tasks.py` (update_stale_prices function)
- Modify: `models.py` (add price_drop notification type)
- Test: `tests/unit/test_price_alerts.py` (new file)

**Step 1: Write failing price drop test**

Create `tests/unit/test_price_alerts.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

def test_price_drop_detection(app, user, other_user):
    """Test that 10%+ price drop is detected."""
    from models import Item, PriceHistory, Notification, db
    from services.tasks import update_stale_prices

    # Create item with initial price
    item = Item(
        description="Test Item",
        link="https://www.amazon.com/test",
        price=100.00,
        user_id=user.id,
        status="Available",
        price_last_checked=datetime.now(timezone.utc) - timedelta(days=8)
    )
    db.session.add(item)
    db.session.commit()

    # Record initial price in history
    history = PriceHistory(
        item_id=item.id,
        price=100.00,
        recorded_at=datetime.now(timezone.utc) - timedelta(days=8)
    )
    db.session.add(history)
    db.session.commit()

    # Mock price fetch to return 10% drop
    with patch('services.price_service.fetch_price', return_value=85.00):
        update_stale_prices()

    # Notification should be created for other users
    notif = Notification.query.filter_by(
        user_id=other_user.id,
        type='price_drop'
    ).first()

    assert notif is not None
    assert 'Price drop' in notif.message
    assert '15%' in notif.message or '15.0%' in notif.message

def test_no_alert_for_item_owner(app, user):
    """Owner should not receive price drop alerts (surprise protection)."""
    from models import Item, PriceHistory, Notification, db
    from services.tasks import update_stale_prices

    item = Item(
        description="Owner's Item",
        link="https://www.amazon.com/test",
        price=100.00,
        user_id=user.id,
        status="Available",
        price_last_checked=datetime.now(timezone.utc) - timedelta(days=8)
    )
    db.session.add(item)
    db.session.commit()

    history = PriceHistory(
        item_id=item.id,
        price=100.00,
        recorded_at=datetime.now(timezone.utc) - timedelta(days=8)
    )
    db.session.add(history)
    db.session.commit()

    with patch('services.price_service.fetch_price', return_value=85.00):
        update_stale_prices()

    # Owner should NOT receive notification
    notif = Notification.query.filter_by(
        user_id=user.id,
        type='price_drop'
    ).first()

    assert notif is None

def test_no_alert_for_small_drop(app, user, other_user):
    """Drops < 10% should not trigger alerts."""
    from models import Item, PriceHistory, Notification, db
    from services.tasks import update_stale_prices

    item = Item(
        description="Test Item",
        link="https://www.amazon.com/test",
        price=100.00,
        user_id=user.id,
        status="Available",
        price_last_checked=datetime.now(timezone.utc) - timedelta(days=8)
    )
    db.session.add(item)
    db.session.commit()

    history = PriceHistory(
        item_id=item.id,
        price=100.00,
        recorded_at=datetime.now(timezone.utc) - timedelta(days=8)
    )
    db.session.add(history)
    db.session.commit()

    # 8% drop (below threshold)
    with patch('services.price_service.fetch_price', return_value=92.00):
        update_stale_prices()

    # No notification should be created
    notif = Notification.query.filter_by(type='price_drop').first()
    assert notif is None
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_price_alerts.py::test_price_drop_detection -v
```

Expected: FAIL (price drop logic doesn't exist yet)

**Step 3: Update Notification model to support price_drop type**

In `models.py`, verify Notification.type field allows 'price_drop'. If it's an Enum or has validation, add it:

```python
# In Notification class, ensure type field allows 'price_drop'
# If using Enum:
class NotificationType(str, Enum):
    CLAIM = 'claim'
    COMMENT = 'comment'
    PRICE_DROP = 'price_drop'
    # ... other types

# Or if just a string field, it should work as-is
```

**Step 4: Implement price drop detection in tasks.py**

In `services/tasks.py`, modify `update_stale_prices()`:

```python
def update_stale_prices():
    """Update prices for items older than 7 days and send alerts on drops."""
    from app import create_app
    from models import Item, PriceHistory, Notification, User, db
    from services.price_service import fetch_price
    from datetime import datetime, timezone, timedelta
    import logging

    logger = logging.getLogger(__name__)
    app = create_app()

    with app.app_context():
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stale_items = Item.query.filter(
            Item.link.isnot(None),
            Item.price_last_checked < stale_cutoff
        ).all()

        logger.info(f"Updating {len(stale_items)} stale item prices")

        for item in stale_items:
            try:
                # Fetch new price
                new_price = fetch_price(item.link)

                if new_price and new_price != item.price:
                    # Get last recorded price for comparison
                    last_history = PriceHistory.query.filter_by(
                        item_id=item.id
                    ).order_by(PriceHistory.recorded_at.desc()).first()

                    old_price = last_history.price if last_history else item.price

                    # Check for significant drop (10%+)
                    if old_price and new_price < old_price:
                        drop_pct = ((old_price - new_price) / old_price) * 100

                        if drop_pct >= 10:
                            _create_price_drop_alert(item, old_price, new_price, drop_pct)
                            logger.info(f"Price drop alert: {item.description} dropped {drop_pct:.0f}%")

                    # Update item price
                    item.price = new_price
                    item.price_last_checked = datetime.now(timezone.utc)

                    # Record in history
                    history = PriceHistory(
                        item_id=item.id,
                        price=new_price,
                        recorded_at=datetime.now(timezone.utc)
                    )
                    db.session.add(history)

                db.session.commit()

            except Exception as e:
                logger.error(f"Price update failed for item {item.id}: {e}")
                db.session.rollback()

def _create_price_drop_alert(item, old_price, new_price, drop_pct):
    """Create price drop notifications for all users except item owner.

    Args:
        item: Item with price drop
        old_price: Previous price
        new_price: New (lower) price
        drop_pct: Percentage drop
    """
    from models import User, Notification, db
    from datetime import datetime, timezone

    # Get all users except item owner (surprise protection)
    users = User.query.filter(User.id != item.user_id).all()

    message = (
        f"Price drop on {item.description}! "
        f"${old_price:.2f} → ${new_price:.2f} ({drop_pct:.0f}% off)"
    )

    for user in users:
        notification = Notification(
            user_id=user.id,
            type='price_drop',
            message=message,
            item_id=item.id,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(notification)
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_price_alerts.py -v
```

Expected: PASS (all price drop tests)

**Step 6: Commit**

```bash
git add services/tasks.py models.py tests/unit/test_price_alerts.py
git commit -m "feat: add price drop detection to update task

- Detect 10%+ price drops in update_stale_prices()
- Create price_drop notifications for all users except owner
- Respect surprise protection (owners don't see alerts)
- Add comprehensive price alert tests"
```

---

### Task 5: Browser Test for Price Drop Alerts

**Files:**
- Create: `tests/browser/test_price_alerts.py`

**Step 1: Write browser test for price drop notification**

Create `tests/browser/test_price_alerts.py`:

```python
import pytest
from playwright.sync_api import Page, expect
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

def test_price_drop_shows_notification(page: Page, live_server, authenticated_user):
    """Test that price drop creates visible notification."""
    from models import Item, PriceHistory, db

    user = authenticated_user

    # Create another user (to receive the alert)
    from models import User
    other = User(name="Other User", email="other@example.com")
    db.session.add(other)
    db.session.commit()

    # Create item with old price
    item = Item(
        description="Expensive Gadget",
        link="https://www.amazon.com/test-product",
        price=100.00,
        user_id=user.id,
        status="Available",
        price_last_checked=datetime.now(timezone.utc) - timedelta(days=8)
    )
    db.session.add(item)
    db.session.commit()

    # Record price history
    history = PriceHistory(
        item_id=item.id,
        price=100.00,
        recorded_at=datetime.now(timezone.utc) - timedelta(days=8)
    )
    db.session.add(history)
    db.session.commit()

    # Simulate price drop task
    with patch('services.price_service.fetch_price', return_value=75.00):
        from services.tasks import update_stale_prices
        update_stale_prices()

    # Login as other user (who should see the alert)
    page.goto(f"{live_server.url()}/logout")
    page.goto(f"{live_server.url()}/login")
    page.fill('input[name="email"]', "other@example.com")
    page.fill('input[name="password"]', "wishlist2025")  # Family password
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')

    # Check for notification bell badge
    expect(page.locator('.notification-badge')).to_be_visible()

    # Click notifications to open dropdown
    page.click('.notification-bell')

    # Verify price drop notification appears
    notification_text = page.locator('.notification-item').first
    expect(notification_text).to_contain_text('Price drop')
    expect(notification_text).to_contain_text('Expensive Gadget')
    expect(notification_text).to_contain_text('25%')
```

**Step 2: Run browser test**

```bash
pytest tests/browser/test_price_alerts.py -v
```

Expected: PASS (notification appears in UI)

**Step 3: Commit**

```bash
git add tests/browser/test_price_alerts.py
git commit -m "test: add browser test for price drop notifications

- Verify notification appears in UI after price drop
- Test notification badge and dropdown display
- End-to-end validation of price alert feature"
```

---

## Final Steps

### Task 6: Update Documentation

**Files:**
- Modify: `docs/IMPROVEMENTS.md` (mark items complete)
- Modify: `README.md` (if needed)

**Step 1: Update IMPROVEMENTS.md**

Mark completed items:
- Technical Debt: "No input sanitization - **XSS Risk**" → ✅ Complete
- Add note about Phase 1 completion (Price Drop Alerts)

**Step 2: Commit documentation**

```bash
git add docs/IMPROVEMENTS.md
git commit -m "docs: mark security fixes and price alerts as complete

- DELETE-via-GET CSRF bypass fixed
- SSRF protection added
- URL XSS validation added
- Price drop alerts implemented"
```

---

## Summary

**Phase 0 (Security):**
- Task 1: DELETE via GET fix (15 min)
- Task 2: SSRF protection (30 min)
- Task 3: URL scheme validation (30 min)

**Phase 1 (Alerts):**
- Task 4: Price drop detection (2 hrs)
- Task 5: Browser test (30 min)
- Task 6: Documentation (15 min)

**Total effort:** ~4 hours
**Test coverage:** 3 new test files, 10+ unit tests, 1 browser test

**Skills referenced:**
- @superpowers:test-driven-development for TDD workflow
- @superpowers:verification-before-completion for final checks
