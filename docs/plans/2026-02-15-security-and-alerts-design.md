# Security Hardening + Price Drop Alerts - Design Document

**Author:** Claude Code (with agent team: prd-analyst, innovation-scout, security-auditor, devils-advocate)
**Date:** 2026-02-15
**Status:** Approved
**Related Issues:** IMPROVEMENTS.md #52 (Price Crawler), Technical Debt (XSS, CSRF)

---

## 1. Executive Summary

This design addresses critical security vulnerabilities and adds a high-value user feature with minimal effort.

**Phases:**
- **Phase 0:** Security Hardening (1-2 hrs) - Fix DELETE-via-GET CSRF bypass, SSRF, URL XSS
- **Phase 1:** Price Drop Alerts (2-3 hrs) - Notify users when item prices fall 10%+
- **Phase 2:** Wishlist Sharing (6-10 hrs, OPTIONAL) - Pending user validation

**Total committed effort:** 3-5 hours
**Business value:** Eliminates active vulnerabilities + delivers user-requested price notifications

---

## 2. Background

### 2.1 Team Analysis Process

A parallel agent team explored upgrade opportunities across three dimensions:
- **prd-analyst:** Evaluated existing PRDs (Sharing, Secret Santa, Price Crawler)
- **innovation-scout:** Brainstormed 5 novel features
- **security-auditor:** Identified TOP 5 technical debt items
- **devils-advocate:** Critiqued all proposals for feasibility and real-world impact

### 2.2 Key Findings

**Security Auditor found:**
1. DELETE via GET - CSRF bypass (HIGH severity)
2. SSRF in price fetching - Can access internal services (HIGH)
3. URL XSS - javascript: scheme not blocked (MEDIUM)
4. Insecure defaults - Hardcoded secrets (MEDIUM)
5. File write issues (needs investigation)

**Devils Advocate validated:**
- Security fixes are CRITICAL and must precede feature work
- Price Drop Alerts is the only innovation proposal with genuine ROI
- Wishlist Sharing should be validated with users before implementation
- Most "innovative" ideas were over-engineered for a 5-20 user family app

**Decision:** Fix security first, add Price Drop Alerts (leverages existing PriceHistory), defer Sharing pending user feedback.

---

## 3. Phase 0: Security Hardening

### 3.1 DELETE via GET Fix

**Problem:**
`blueprints/items.py:413` - `delete_item()` route accepts GET requests:
```python
@bp.route('/delete_item/<int:item_id>')
def delete_item(item_id):
```

This enables CSRF bypass via image tags: `<img src="/delete_item/42">` embedded in comments or external pages can trigger deletions.

**Fix:**
```python
@bp.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    # Existing logic (CSRF auto-checked by Flask-WTF on POST)
```

**Template update** (`templates/items_list.html` or item card):
```html
<!-- Before: -->
<a href="{{ url_for('items.delete_item', item_id=item.id) }}">Delete</a>

<!-- After: -->
<form method="POST" action="{{ url_for('items.delete_item', item_id=item.id) }}" style="display:inline;">
  {{ csrf_token() }}
  <button type="submit" onclick="return confirm('Delete this item?')">Delete</button>
</form>
```

**Testing:**
- GET request to `/delete_item/<id>` returns 405 Method Not Allowed
- POST with valid CSRF token succeeds
- POST without CSRF token returns 400 Bad Request

**Effort:** 15 minutes

---

### 3.2 SSRF Protection

**Problem:**
`services/price_service.py:90` - `_make_request(url)` and `blueprints/api.py:9` - `/api/fetch-metadata` accept arbitrary URLs:
```python
response = session.get(url, headers=headers, timeout=10)
```

An attacker could provide `http://169.254.169.254/latest/meta-data/` (AWS metadata), `http://localhost:5432` (internal PostgreSQL), or other internal services.

**Fix:**
Add URL validator to `services/price_service.py`:

```python
from urllib.parse import urlparse
import ipaddress

BLOCKED_SCHEMES = ['file', 'ftp', 'gopher', 'data']
PRIVATE_IP_RANGES = [
    ipaddress.ip_network('127.0.0.0/8'),    # localhost
    ipaddress.ip_network('10.0.0.0/8'),     # private
    ipaddress.ip_network('172.16.0.0/12'),  # private
    ipaddress.ip_network('192.168.0.0/16'), # private
    ipaddress.ip_network('169.254.0.0/16'), # link-local (AWS metadata)
]

def validate_url(url: str) -> bool:
    """Validate URL is safe for server-side fetch."""
    try:
        parsed = urlparse(url)

        # Only allow http/https
        if parsed.scheme not in ['http', 'https']:
            return False

        # Block private IPs
        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve hostname to IP
        import socket
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)

        for network in PRIVATE_IP_RANGES:
            if ip_obj in network:
                return False

        return True
    except Exception:
        return False

def _make_request(url: str, retries: int = 3):
    if not validate_url(url):
        raise ValueError(f"Invalid or unsafe URL: {url}")

    # ... existing request logic
```

**Update endpoints:**
- `blueprints/api.py:9` - `/api/fetch-metadata` - validate URL before `_make_request()`
- `blueprints/items.py:384` - `/item/<id>/refresh-price` - validate before price fetch

**Testing:**
- `http://169.254.169.254/` rejected
- `http://localhost/` rejected
- `http://10.0.0.1/` rejected
- `file:///etc/passwd` rejected
- `https://amazon.com` allowed

**Effort:** 30 minutes

---

### 3.3 URL Scheme Validation (XSS)

**Problem:**
`item.link` field is rendered in templates as `<a href="{{ item.link }}">`. If a user enters `javascript:alert(document.cookie)`, clicking the link executes the script (XSS).

**Fix:**
Add form validator in `blueprints/items.py` or create new `services/form_validators.py`:

```python
def validate_url_scheme(url: str) -> bool:
    """Ensure URL uses http or https scheme."""
    if not url:
        return True  # Optional field

    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.scheme in ['http', 'https', '']

# In submit_item() and edit_item() routes:
link = request.form.get('link', '').strip()
image_url = request.form.get('image_url', '').strip()

if link and not validate_url_scheme(link):
    flash('Link must be a valid http or https URL', 'error')
    return redirect(...)

if image_url and not validate_url_scheme(image_url):
    flash('Image URL must be a valid http or https URL', 'error')
    return redirect(...)
```

**Testing:**
- `javascript:alert(1)` rejected on item creation
- `data:text/html,<script>alert(1)</script>` rejected
- `https://amazon.com/product` allowed
- Empty link allowed (optional field)

**Effort:** 30 minutes

---

## 4. Phase 1: Price Drop Alerts

### 4.1 Feature Overview

**User Story:**
> As a family member, I want to be notified when an unclaimed item's price drops significantly, so I can buy it at the best price.

**Success Criteria:**
- When a price drops ≥10%, all family members (except item owner) receive notification
- Notification shows old price, new price, and percentage drop
- Clicking notification navigates to item detail
- No notifications sent for owner's own items (surprise protection)

### 4.2 Architecture

**Leverage existing infrastructure:**
- `PriceHistory` model - already tracks historical prices
- `services/tasks.py:update_stale_prices()` - Celery task that refreshes prices hourly
- `Notification` model - already handles user alerts

**New logic:**
```
update_stale_prices()
  ├─ For each item with stale price (7+ days old)
  ├─ Fetch new price via price_service
  ├─ Record in PriceHistory
  ├─ NEW: Check if price dropped ≥10% vs last history record
  └─ NEW: If yes, create Notification for all users except owner
```

### 4.3 Implementation

**Update `services/tasks.py`:**

```python
def update_stale_prices():
    """Update prices for items older than 7 days."""
    with app.app_context():
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stale_items = Item.query.filter(
            Item.link.isnot(None),
            Item.price_last_checked < stale_cutoff
        ).all()

        for item in stale_items:
            try:
                # Fetch new price
                new_price = fetch_price(item.link)

                if new_price and new_price != item.price:
                    # Get last recorded price
                    last_history = PriceHistory.query.filter_by(
                        item_id=item.id
                    ).order_by(PriceHistory.recorded_at.desc()).first()

                    old_price = last_history.price if last_history else item.price

                    # Check for significant drop
                    if old_price and new_price < old_price:
                        drop_pct = ((old_price - new_price) / old_price) * 100
                        if drop_pct >= 10:
                            _create_price_drop_alert(item, old_price, new_price, drop_pct)

                    # Update item
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
    """Create notifications for price drop."""
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

**Update `models.py` (if needed):**
Add `type='price_drop'` to Notification types (currently supports 'claim', 'comment', etc.)

**Frontend:**
Notifications already render in navbar bell. Price drop notifications will appear with existing styling.

### 4.4 Testing

**Unit tests** (`tests/unit/test_price_alerts.py`):
```python
def test_price_drop_creates_notification(app, user, other_user):
    """Test that 10%+ price drop creates notifications."""
    item = create_item(user=user, price=100.00)

    # Simulate price drop
    with patch('services.price_service.fetch_price', return_value=85.00):
        update_stale_prices()

    # Check notification created for other users
    notif = Notification.query.filter_by(user_id=other_user.id, type='price_drop').first()
    assert notif is not None
    assert 'Price drop' in notif.message
    assert '15% off' in notif.message

def test_no_alert_for_item_owner(app, user):
    """Owners don't get price drop alerts (surprise protection)."""
    item = create_item(user=user, price=100.00)

    with patch('services.price_service.fetch_price', return_value=85.00):
        update_stale_prices()

    notif = Notification.query.filter_by(user_id=user.id, type='price_drop').first()
    assert notif is None

def test_no_alert_for_small_drop(app, user, other_user):
    """Drops <10% don't trigger alerts."""
    item = create_item(user=user, price=100.00)

    with patch('services.price_service.fetch_price', return_value=92.00):  # 8% drop
        update_stale_prices()

    notif = Notification.query.filter_by(type='price_drop').first()
    assert notif is None
```

**Browser test** (`tests/browser/test_price_alerts.py`):
- Create item with price $100
- Mock price fetch to return $80
- Trigger price update task
- Navigate to notifications
- Verify "Price drop" notification appears with correct percentage

**Effort:** 2-3 hours

---

## 5. Phase 2: Wishlist Sharing (DEFERRED)

**Status:** Pending user validation
**Rationale:** Devils-advocate challenged the premise that external sharing is needed when family already has Family Code access. Screenshots/forwarding may solve 90% of the use case.

**Decision point:** After Phase 0+1 complete (~3-5 hours), ask actual app users:
- "Would you find it useful to share your wishlist with non-family (Grammy, friends) via a link?"
- If yes (3+ users request it) → proceed with PRD_WISHLIST_SHARING.md
- If no → explore other high-value features

**If approved:** Add these improvements to the PRD:
- Mobile responsive design (currently missing)
- Testing budget: 3-4 hours (not 1-2)
- Rate limiting on public `/wishlist/share/<token>` route
- Analytics: track share link creation/views to validate feature usage

---

## 6. Implementation Plan

### 6.1 Phase 0: Security (1-2 hrs)

**Sprint tasks:**
1. Fix DELETE-via-GET (15 min)
   - Update route to `methods=['POST']`
   - Update template to form submission
   - Test: GET returns 405, POST succeeds

2. Add SSRF protection (30 min)
   - Create `validate_url()` in price_service
   - Block private IPs, non-HTTP schemes
   - Update `/api/fetch-metadata` and `/refresh-price`
   - Test: blocked URLs rejected, valid URLs allowed

3. URL scheme validation (30 min)
   - Add `validate_url_scheme()` form validator
   - Update submit/edit item routes
   - Test: javascript: rejected, https: allowed

### 6.2 Phase 1: Price Drop Alerts (2-3 hrs)

**Sprint tasks:**
1. Update task logic (1 hr)
   - Enhance `update_stale_prices()` with drop detection
   - Add `_create_price_drop_alert()` helper
   - Test drop percentage calculation

2. Unit tests (1 hr)
   - Test notification creation on 10%+ drop
   - Test no notification for owner (surprise protection)
   - Test no notification for <10% drop
   - Test edge cases (no history, price increase)

3. Browser test (30 min)
   - End-to-end flow: item created → price drops → notification appears
   - Verify notification link navigates to item

### 6.3 Rollout

**Deployment order:**
1. Phase 0 (security) → Deploy immediately as hotfix
2. Phase 1 (alerts) → Deploy after full test pass
3. Phase 2 (sharing) → Only if validated by users

**Monitoring:**
- Sentry for errors on new validation logic
- Check notification delivery rate post-deployment
- Monitor price fetch success rate (should not degrade)

---

## 7. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SSRF validation bypassed via DNS rebinding | Low | High | Pre-resolve DNS, check IP ranges |
| Price drop alerts spam users | Medium | Low | Require 10% threshold, limit to once per item |
| URL validation breaks existing links | Low | Medium | Test against existing item URLs before deploy |
| Price fetch failures increase | Low | Medium | Validate URLs before storage, not just fetch time |

---

## 8. Success Metrics

**Phase 0 (Security):**
- Zero CSRF-based deletions after deploy
- Zero SSRF attempts succeed
- Zero XSS vectors via item links

**Phase 1 (Alerts):**
- 80%+ of price drops ≥10% trigger notifications
- <5% false positive rate (notifications for <10% drops)
- Users claim items within 48 hours of price drop alert (anecdotal)

---

## 9. Open Questions

1. **Price drop threshold:** Is 10% the right number, or should it be configurable per user?
2. **Alert frequency:** Should we limit alerts to 1 per item per week to avoid spam?
3. **Email vs in-app:** Should price drops also send email, or just in-app notifications?

**Decisions:**
- Start with 10% fixed threshold, gather feedback
- No alert frequency limit in V1 (most items don't fluctuate rapidly)
- In-app only in V1, add email in V2 if requested

---

## 10. Conclusion

This design delivers immediate security value (Phase 0) and a high-ROI user feature (Phase 1) in under 5 hours of work. By validating Wishlist Sharing with actual users before implementation, we avoid building features nobody asked for.

**Next steps:**
1. Create implementation plan via writing-plans skill
2. Execute with agent team
3. Deploy security fixes as hotfix
4. Deploy price alerts after testing
5. Survey users about sharing feature interest
