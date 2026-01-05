# PRD: Price Crawler Improvements

**Author:** Claude Code
**Created:** 2026-01-04
**Status:** Draft
**Related Improvement:** #35 (Price Tracking), New
**Estimated Effort:** 12-16 hours (phased)

---

## 1. Overview

### 1.1 Problem Statement

The current `services/price_service.py` provides price fetching capabilities, but faces several challenges:

| Issue | Impact | Current Behavior |
|-------|--------|------------------|
| **Amazon blocking** | ~60% of items are Amazon links | CAPTCHA/bot detection blocks most requests |
| **No price history** | Users can't see price trends | Only current price stored |
| **Sequential processing** | Slow batch updates | 2-3 sec per item = hours for large lists |
| **Stale selectors** | Extraction failures | Sites change HTML frequently |
| **No caching** | Redundant requests | Same URL fetched multiple times |
| **Limited monitoring** | Silent failures | No alerts when extraction rates drop |
| **Resource-heavy fallback** | Playwright is slow | 5-10 sec per page, high memory |

### 1.2 Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    price_service.py                          │
│                                                              │
│  fetch_price(url) ──┬── _fetch_amazon_price()               │
│                     ├── _fetch_target_price()                │
│                     ├── _fetch_walmart_price()               │
│                     ├── _fetch_bestbuy_price()               │
│                     ├── _fetch_etsy_price()                  │
│                     └── _fetch_generic_price()               │
│                              │                               │
│                              ▼                               │
│                    _make_request() ◄─── Retry logic          │
│                              │                               │
│                              ▼                               │
│                    BeautifulSoup parsing                     │
│                              │                               │
│                              ▼ (fallback)                    │
│                    _fetch_with_playwright()                  │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Proposed Improvements

This PRD covers improvements across 4 phases:

1. **Phase 1: Reliability** - Caching, better error handling, monitoring
2. **Phase 2: Performance** - Concurrent fetching, smarter scheduling ✅ *Implemented*
3. **Phase 3: Price History** - Track prices over time, visualize trends ✅ *Implemented*
4. **Phase 4: Advanced Extraction** - Proxy support, AI-assisted parsing

---

## 2. User Stories

> **As a wishlist user**, I want to see price history for my items, so I know if now is a good time to buy.

> **As a gift giver**, I want reliable price updates, so I know the actual cost of items I'm considering.

> **As an admin**, I want visibility into extraction success rates, so I can fix broken selectors quickly.

> **As a user with Amazon items**, I want prices to update even though Amazon blocks scrapers, so my wishlist stays accurate.

---

## 3. Phase 1: Reliability & Monitoring

**Effort:** 4-5 hours

### 3.1 Request Caching (Redis)

Cache successful responses to avoid redundant fetches.

```python
# New: Cache layer
CACHE_TTL = 3600  # 1 hour for price data

def _get_cached_or_fetch(url: str) -> Optional[str]:
    """Check cache before making request."""
    cache_key = f"price:html:{hashlib.md5(url.encode()).hexdigest()}"

    cached = redis_client.get(cache_key)
    if cached:
        return cached.decode()

    response = _make_request(url)
    if response and response.ok:
        redis_client.setex(cache_key, CACHE_TTL, response.text)
        return response.text

    return None
```

**Benefits:**
- Reduces duplicate requests when users refresh multiple times
- Faster responses for recently-fetched URLs
- Reduces bot detection risk (fewer requests)

### 3.2 Extraction Metrics

Track success/failure rates per domain.

```python
# New model
class PriceExtractionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), nullable=False, index=True)
    url = db.Column(db.String(2048))
    success = db.Column(db.Boolean, nullable=False)
    price = db.Column(db.Float, nullable=True)
    extraction_method = db.Column(db.String(50))  # 'meta', 'jsonld', 'selector', 'playwright'
    error_type = db.Column(db.String(50))  # 'captcha', 'timeout', 'no_price', 'blocked'
    response_time_ms = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Dashboard Metrics:**
- Success rate by domain (last 24h, 7d, 30d)
- Average response time by domain
- Most common error types
- Items with stale prices (>14 days)

### 3.3 Improved Error Classification

```python
class ExtractionError(Enum):
    CAPTCHA = "captcha"
    BOT_BLOCKED = "bot_blocked"
    TIMEOUT = "timeout"
    NO_PRICE_FOUND = "no_price_found"
    INVALID_PAGE = "invalid_page"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"

def _classify_error(response, soup) -> ExtractionError:
    """Classify extraction failure for better handling."""
    if response is None:
        return ExtractionError.NETWORK_ERROR

    text_lower = response.text.lower()

    if 'captcha' in text_lower or 'robot check' in text_lower:
        return ExtractionError.CAPTCHA
    if response.status_code == 429:
        return ExtractionError.RATE_LIMITED
    if response.status_code == 403:
        return ExtractionError.BOT_BLOCKED
    if 'not found' in text_lower or response.status_code == 404:
        return ExtractionError.INVALID_PAGE

    return ExtractionError.NO_PRICE_FOUND
```

### 3.4 Alerting Integration

Send alerts when extraction rates drop below threshold.

```python
def check_extraction_health():
    """Check extraction health and send alerts if needed."""
    threshold = 0.5  # Alert if <50% success

    stats = db.session.query(
        PriceExtractionLog.domain,
        func.count().label('total'),
        func.sum(case((PriceExtractionLog.success, 1), else_=0)).label('success')
    ).filter(
        PriceExtractionLog.created_at > datetime.utcnow() - timedelta(hours=24)
    ).group_by(PriceExtractionLog.domain).all()

    for domain, total, success in stats:
        if total >= 10 and (success / total) < threshold:
            send_admin_alert(
                f"Price extraction failing for {domain}",
                f"Success rate: {success}/{total} ({success/total:.0%})"
            )
```

---

## 4. Phase 2: Performance Optimization

**Effort:** 3-4 hours

### 4.1 Concurrent Fetching

Process multiple URLs simultaneously using async.

```python
import asyncio
import aiohttp

async def fetch_prices_batch(urls: List[str], max_concurrent: int = 5) -> Dict[str, float]:
    """Fetch multiple prices concurrently."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(url: str) -> Tuple[str, Optional[float]]:
        async with semaphore:
            # Add jitter to avoid thundering herd
            await asyncio.sleep(random.uniform(0.5, 1.5))
            price = await _fetch_price_async(url)
            return url, price

    tasks = [fetch_one(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {url: price for url, price in results if not isinstance(price, Exception)}
```

**Performance Impact:**
- Current: 100 items × 3 sec = ~5 minutes
- With concurrency (5x): 100 items ÷ 5 × 3 sec = ~1 minute

### 4.2 Smart Scheduling

Prioritize items based on factors:

```python
def get_items_needing_update(limit: int = 50) -> List[Item]:
    """Get items prioritized for price update."""

    # Priority factors:
    # 1. Never updated (NULL price_updated_at) - highest
    # 2. Items with recent claims (people are interested)
    # 3. Items with events coming up in <14 days
    # 4. Regular staleness (>7 days)

    priority_score = case(
        (Item.price_updated_at.is_(None), 100),
        (Item.status == 'Claimed', 80),
        (Item.event_id.isnot(None), 70),
        else_=50
    ) - func.extract('epoch', func.now() - Item.price_updated_at) / 86400

    return Item.query.filter(
        Item.link.isnot(None),
        Item.link != '',
        db.or_(
            Item.price_updated_at.is_(None),
            Item.price_updated_at < datetime.utcnow() - timedelta(days=7)
        )
    ).order_by(priority_score.desc()).limit(limit).all()
```

### 4.3 Domain-Specific Rate Limiting

Different domains have different tolerance:

```python
DOMAIN_RATE_LIMITS = {
    'amazon.com': 5.0,      # Very aggressive blocking
    'target.com': 2.0,
    'walmart.com': 2.0,
    'bestbuy.com': 1.5,
    'etsy.com': 1.5,
    'default': 1.0
}

def get_rate_limit(domain: str) -> float:
    """Get rate limit for domain."""
    for key, limit in DOMAIN_RATE_LIMITS.items():
        if key in domain:
            return limit
    return DOMAIN_RATE_LIMITS['default']
```

---

## 5. Phase 3: Price History ✅ IMPLEMENTED

**Status:** Complete (2026-01-04)
**Files Created:**
- `models.py` - Added `PriceHistory` model
- `services/price_history.py` - Recording logic with deduplication
- `blueprints/api.py` - `/api/items/<id>/price-history` endpoint
- `static/js/sparkline.js` - Canvas-based sparkline rendering
- `templates/partials/_item_card.html` - Sparkline container
- `tests/unit/test_price_history.py` - Unit tests
- `tests/browser/test_price_history_ui.py` - Browser test

**Effort:** 4-5 hours

### 5.1 Database Schema

```python
class PriceHistory(db.Model):
    """Track historical prices for items."""
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    source = db.Column(db.String(50))  # 'auto', 'manual', 'initial'

    item = db.relationship('Item', backref='price_history')

    __table_args__ = (
        db.Index('idx_price_history_item_date', 'item_id', 'recorded_at'),
    )
```

### 5.2 Recording Logic

```python
def record_price(item: Item, price: float, source: str = 'auto'):
    """Record a price point, avoiding duplicates within 6 hours."""

    # Check for recent duplicate
    recent = PriceHistory.query.filter(
        PriceHistory.item_id == item.id,
        PriceHistory.recorded_at > datetime.utcnow() - timedelta(hours=6)
    ).order_by(PriceHistory.recorded_at.desc()).first()

    # Only record if price changed or no recent record
    if not recent or abs(recent.price - price) > 0.01:
        history = PriceHistory(
            item_id=item.id,
            price=price,
            source=source
        )
        db.session.add(history)
```

### 5.3 Price Trend API

```python
@bp.route('/api/items/<int:item_id>/price-history')
@login_required
def get_price_history(item_id):
    """Get price history for an item."""
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)

    history = PriceHistory.query.filter_by(item_id=item_id)\
        .order_by(PriceHistory.recorded_at.desc())\
        .limit(90).all()  # Last 90 days max

    return jsonify({
        'item_id': item_id,
        'current_price': item.price,
        'history': [
            {'price': h.price, 'date': h.recorded_at.isoformat()}
            for h in reversed(history)
        ],
        'stats': {
            'lowest': min(h.price for h in history) if history else None,
            'highest': max(h.price for h in history) if history else None,
            'average': sum(h.price for h in history) / len(history) if history else None
        }
    })
```

### 5.4 UI: Price Sparkline

Add a mini chart to item cards showing price trend:

```html
<!-- In _item_card.html -->
{% if item.price_history and item.price_history|length > 1 %}
<div class="price-sparkline"
     data-prices="{{ item.price_history|map(attribute='price')|list|tojson }}"
     title="Price trend (last 30 days)">
    <canvas width="60" height="20"></canvas>
</div>
{% endif %}
```

```javascript
// Simple sparkline with Canvas
document.querySelectorAll('.price-sparkline').forEach(el => {
    const prices = JSON.parse(el.dataset.prices);
    const canvas = el.querySelector('canvas');
    const ctx = canvas.getContext('2d');

    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;

    ctx.strokeStyle = prices[prices.length-1] < prices[0] ? '#28a745' : '#dc3545';
    ctx.lineWidth = 1.5;
    ctx.beginPath();

    prices.forEach((price, i) => {
        const x = (i / (prices.length - 1)) * canvas.width;
        const y = canvas.height - ((price - min) / range) * canvas.height;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });

    ctx.stroke();
});
```

### 5.5 Price Drop Detection Enhancement

Improve notifications with context:

```python
def check_price_drop(item: Item, old_price: float, new_price: float):
    """Check for price drop and send enhanced notification."""
    if old_price is None or new_price >= old_price:
        return

    drop_percent = ((old_price - new_price) / old_price) * 100

    # Get historical context
    history = PriceHistory.query.filter_by(item_id=item.id)\
        .order_by(PriceHistory.recorded_at.desc()).limit(30).all()

    all_time_low = min(h.price for h in history) if history else new_price

    message_parts = [f"Price drop on '{item.description[:40]}'!"]
    message_parts.append(f"${new_price:.2f} (was ${old_price:.2f}, -{drop_percent:.0f}%)")

    if new_price <= all_time_low:
        message_parts.append("This is the LOWEST price we've seen!")

    # Notify owner
    create_notification(
        user_id=item.user_id,
        message=" ".join(message_parts),
        link=f"/items?user_filter={item.user_id}"
    )
```

---

## 6. Phase 4: Advanced Extraction (Future)

**Effort:** 6-8 hours (optional/future)

### 6.1 Proxy Rotation

For high-volume scraping or blocked domains:

```python
class ProxyManager:
    """Manage rotating proxies for requests."""

    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.failures = defaultdict(int)
        self.last_used = defaultdict(float)

    def get_proxy(self, domain: str) -> Optional[str]:
        """Get best proxy for domain, avoiding recently used ones."""
        available = [
            p for p in self.proxies
            if self.failures[p] < 3
            and time.time() - self.last_used[p] > 30
        ]

        if not available:
            return None

        proxy = random.choice(available)
        self.last_used[proxy] = time.time()
        return proxy

    def mark_failure(self, proxy: str):
        self.failures[proxy] += 1

    def mark_success(self, proxy: str):
        self.failures[proxy] = 0
```

### 6.2 Browser Fingerprint Rotation

Make Playwright requests look more human:

```python
BROWSER_PROFILES = [
    {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...',
        'viewport': {'width': 1440, 'height': 900},
        'locale': 'en-US',
        'timezone_id': 'America/New_York',
    },
    {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
        'viewport': {'width': 1920, 'height': 1080},
        'locale': 'en-US',
        'timezone_id': 'America/Los_Angeles',
    },
    # ... more profiles
]

def get_stealth_context(browser):
    """Create a browser context with randomized fingerprint."""
    profile = random.choice(BROWSER_PROFILES)

    return browser.new_context(
        user_agent=profile['user_agent'],
        viewport=profile['viewport'],
        locale=profile['locale'],
        timezone_id=profile['timezone_id'],
        # Anti-detection measures
        java_script_enabled=True,
        has_touch=random.choice([True, False]),
        device_scale_factor=random.choice([1, 2]),
    )
```

### 6.3 AI-Assisted Price Extraction (Experimental)

Use LLM for pages where selectors fail:

```python
async def extract_price_with_llm(html: str, url: str) -> Optional[float]:
    """Last resort: ask LLM to find price in HTML."""

    # Truncate to relevant part
    soup = BeautifulSoup(html, 'html.parser')

    # Remove scripts, styles, nav, footer
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()

    text = soup.get_text(separator=' ', strip=True)[:5000]

    response = await anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": f"""Extract the product price from this text.
Return ONLY the numeric price (e.g., "29.99") or "NOT_FOUND".

URL: {url}
Text: {text}"""
        }]
    )

    result = response.content[0].text.strip()

    if result != "NOT_FOUND":
        try:
            return float(result.replace('$', '').replace(',', ''))
        except ValueError:
            pass

    return None
```

### 6.4 Amazon Product Advertising API

For reliable Amazon prices, consider the official API:

```python
# Note: Requires Amazon Associates account
from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.get_items_request import GetItemsRequest

class AmazonProductAPI:
    """Official Amazon Product Advertising API client."""

    def __init__(self, access_key, secret_key, partner_tag):
        self.api = DefaultApi(
            access_key=access_key,
            secret_key=secret_key,
            partner_tag=partner_tag,
            host='webservices.amazon.com',
            region='us-east-1'
        )

    def get_price(self, asin: str) -> Optional[float]:
        """Get price for Amazon ASIN."""
        request = GetItemsRequest(
            item_ids=[asin],
            resources=['Offers.Listings.Price']
        )

        response = self.api.get_items(request)

        if response.items_result and response.items_result.items:
            item = response.items_result.items[0]
            if item.offers and item.offers.listings:
                price = item.offers.listings[0].price
                return price.amount

        return None
```

**Note:** Amazon PA-API requires affiliate account and has strict rate limits (1 req/sec).

---

## 7. Implementation Plan

### Phase 1: Reliability (Week 1)
1. Add Redis caching for HTML responses
2. Create `PriceExtractionLog` model and migration
3. Implement error classification
4. Add health check endpoint for monitoring
5. Write tests for new caching layer

### Phase 2: Performance (Week 2)
1. Implement async batch fetching
2. Add domain-specific rate limiting
3. Implement smart scheduling algorithm
4. Update Celery task to use new batch processor
5. Performance testing

### Phase 3: Price History (Week 3)
1. Create `PriceHistory` model and migration
2. Update price recording to log history
3. Add price history API endpoint
4. Implement sparkline visualization
5. Enhance price drop notifications
6. Write tests

### Phase 4: Advanced (Future)
- Proxy rotation (when needed)
- Browser fingerprint rotation (when needed)
- LLM extraction (experimental)
- Amazon PA-API integration (if affiliate account available)

---

## 8. Database Migrations

### 8.1 Price Extraction Log

```python
def upgrade():
    op.create_table('price_extraction_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('url', sa.String(2048)),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('price', sa.Float()),
        sa.Column('extraction_method', sa.String(50)),
        sa.Column('error_type', sa.String(50)),
        sa.Column('response_time_ms', sa.Integer()),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow)
    )
    op.create_index('idx_extraction_log_domain', 'price_extraction_log', ['domain'])
    op.create_index('idx_extraction_log_created', 'price_extraction_log', ['created_at'])
```

### 8.2 Price History

```python
def upgrade():
    op.create_table('price_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('item.id'), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('source', sa.String(50))
    )
    op.create_index('idx_price_history_item_date', 'price_history', ['item_id', 'recorded_at'])
```

---

## 9. Testing Requirements

### 9.1 Unit Tests

| Test Case | Expected Result |
|-----------|-----------------|
| Cache hit returns cached content | No network request made |
| Cache miss fetches and stores | Response cached for TTL |
| Extraction log records success | Log entry with method |
| Extraction log records failure | Log entry with error type |
| Error classification for CAPTCHA | Returns `ExtractionError.CAPTCHA` |
| Price history records change | New entry created |
| Price history skips duplicate | No entry within 6 hours |
| Sparkline data API | Returns history array |

### 9.2 Integration Tests

| Test | Steps |
|------|-------|
| End-to-end price fetch | Fetch price → Verify cached → Log recorded |
| Batch update with concurrency | Queue 10 items → Verify parallel execution |
| Price drop notification | Old price → Lower price → Notification sent |

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sites change HTML structure | Extraction fails | Monitoring + alerts, selector versioning |
| Rate limiting blocks IP | All requests fail | Domain-specific limits, proxy rotation (Phase 4) |
| Redis unavailable | Cache misses | Graceful fallback to direct fetch |
| Price history grows large | Slow queries | Index + retention policy (keep 90 days) |
| Async complexity | Debugging harder | Good logging, limit concurrency |

---

## 11. Future Considerations

### 11.1 Out of Scope (This PRD)

- Price comparison across retailers
- Price prediction/forecasting
- Browser extension for price capture
- User-contributed price data
- Inventory/availability tracking

### 11.2 Potential Enhancements

- **Price alerts**: "Notify me when price drops below $X"
- **Deal aggregation**: Show current deals across wishlists
- **Retailer health dashboard**: Public status page for extraction
- **Community selectors**: Let users contribute CSS selectors
- **Mobile push notifications**: Price drops via app notifications

---

## 12. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Extraction success rate (all domains) | ~40% | >75% |
| Amazon extraction success rate | ~10% | >50% (with caching/Playwright) |
| Batch update time (100 items) | ~5 min | <2 min |
| Price history data points | 0 | 30+ per active item |
| False positive price drops | Unknown | <5% |

---

## 13. Appendix

### 13.1 Current Supported Domains

| Domain | Strategy | Success Rate |
|--------|----------|--------------|
| Amazon | Selectors + Playwright fallback | Low (~10%) |
| Target | API + selectors | Medium (~60%) |
| Walmart | Selectors + JSON-LD | Medium (~50%) |
| Best Buy | Selectors + JSON-LD | Medium (~55%) |
| Etsy | Selectors + JSON-LD | High (~75%) |
| Generic | Meta tags + JSON-LD + selectors | Variable |

### 13.2 File Structure After Implementation

```
services/
├── price_service.py          # Main service (existing)
├── price_cache.py            # New: Redis caching layer
├── price_history.py          # New: History tracking
├── price_metrics.py          # New: Extraction logging
├── price_extractors/         # New: Domain-specific extractors
│   ├── __init__.py
│   ├── amazon.py
│   ├── target.py
│   ├── walmart.py
│   ├── generic.py
│   └── base.py
└── proxy_manager.py          # Phase 4: Proxy rotation
```

### 13.3 Related Documentation

- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Project roadmap
- [services/price_service.py](../services/price_service.py) - Current implementation
- [tests/unit/test_price_service.py](../tests/unit/test_price_service.py) - Existing tests
