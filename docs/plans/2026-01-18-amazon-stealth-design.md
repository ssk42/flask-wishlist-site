# Design: Full Stealth Playwright for Amazon Price Extraction

**Author:** Claude Code
**Created:** 2026-01-18
**Status:** Approved
**Related:** PRD_PRICE_CRAWLER.md, Improvement #35

---

## 1. Problem Statement

Amazon price extraction currently has a ~10% success rate due to aggressive bot detection (CAPTCHAs, request blocking). The target is 50-60% success rate using free solutions.

**Constraints:**
- Must be free (no proxy services, no Amazon PA-API)
- Deployed on Heroku with decent resources
- Playwright already integrated as fallback
- Willing to accept moderate complexity for better results

## 2. Solution Overview

Make Playwright requests indistinguishable from real human browsing through three layers:

```
┌─────────────────────────────────────────────────────────────┐
│                  Amazon Price Extraction                     │
│                                                              │
│  1. BROWSER IDENTITY LAYER                                   │
│     - Randomized fingerprints (viewport, WebGL, canvas)      │
│     - Persistent cookie jar per identity                     │
│     - Stealth patches (remove automation flags)              │
│                                                              │
│  2. BEHAVIOR LAYER                                           │
│     - Human-like mouse movements                             │
│     - Natural scroll patterns                                │
│     - Random delays with variance                            │
│     - Accept cookie banners                                  │
│                                                              │
│  3. REQUEST STRATEGY LAYER                                   │
│     - Identity rotation (10-20 requests per identity)        │
│     - Time-of-day awareness                                  │
│     - Graceful backoff on detection                          │
│     - Fallback chain: stealth → cache → skip                 │
└─────────────────────────────────────────────────────────────┘
```

**Key dependency:** `playwright-stealth` - Python port of puppeteer-stealth that patches common detection vectors.

---

## 3. Browser Identity Layer

Each browser session looks like a unique, real user. Consistency within a session, variation across sessions.

### 3.1 Identity Profile Structure

```python
@dataclass
class BrowserIdentity:
    id: str                 # Unique identifier
    user_agent: str
    viewport: dict          # {"width": 1440, "height": 900}
    timezone: str           # "America/New_York"
    locale: str             # "en-US"
    color_scheme: str       # "light" or "dark"
    device_scale: float     # 1 or 2 (retina)
    webgl_vendor: str       # "Google Inc. (Apple)"
    webgl_renderer: str     # "ANGLE (Apple, Apple M1, OpenGL 4.1)"

    # Persistence
    cookie_file: str        # Path to stored cookies
    requests_made: int      # Track usage, rotate after 10-20
    burned_until: datetime  # None if healthy
```

### 3.2 Identity Pool

Pre-define 10-15 realistic profiles matching real Mac/Windows/Linux configurations:

```python
IDENTITY_PROFILES = [
    {
        "id": "mac_chrome_1",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "viewport": {"width": 1440, "height": 900},
        "timezone": "America/New_York",
        "locale": "en-US",
        "color_scheme": "light",
        "device_scale": 2,
        "webgl_vendor": "Google Inc. (Apple)",
        "webgl_renderer": "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)",
    },
    {
        "id": "windows_chrome_1",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "timezone": "America/Chicago",
        "locale": "en-US",
        "color_scheme": "dark",
        "device_scale": 1,
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070, OpenGL 4.5)",
    },
    # ... 8-13 more profiles
]
```

### 3.3 Identity Rotation Rules

- Each identity gets its own cookie jar (stored in Redis or filesystem)
- Rotate identities every 10-20 successful requests
- Mark identities as "burned" if they trigger CAPTCHA
- Burned identities cool down for 24 hours

### 3.4 Stealth Patches

Using `playwright-stealth` to:
- Remove `navigator.webdriver` flag
- Spoof `navigator.plugins` and `navigator.languages`
- Override `chrome.runtime` to look like real Chrome
- Add realistic `window.chrome` object
- Mask automation-specific properties

---

## 4. Behavior Layer

Make the browser *act* human, not just *look* human.

### 4.1 Mouse Movement

```python
async def human_mouse_move(page, target_x, target_y):
    """Move mouse in a natural curve, not a straight line."""
    current = await page.evaluate("({x: window.mouseX || 0, y: window.mouseY || 0})")

    # Generate bezier curve with 2-4 control points
    points = generate_bezier_path(
        start=(current['x'], current['y']),
        end=(target_x, target_y),
        control_points=random.randint(2, 4),
        noise=random.uniform(5, 15)
    )

    # Move through points with variable timing
    for point in points:
        await page.mouse.move(point[0], point[1])
        await asyncio.sleep(random.uniform(0.005, 0.030))
```

### 4.2 Scroll Behavior

```python
async def human_scroll(page):
    """Scroll like a human - variable speed, occasional pauses."""
    total_scroll = 0
    target_scroll = random.randint(400, 800)

    while total_scroll < target_scroll:
        # Variable scroll amount
        scroll_amount = random.randint(100, 400)
        await page.mouse.wheel(0, scroll_amount)
        total_scroll += scroll_amount

        # Random pause between scrolls
        await asyncio.sleep(random.uniform(0.2, 0.8))

        # Occasionally scroll back up slightly (5% chance)
        if random.random() < 0.05:
            await page.mouse.wheel(0, -random.randint(30, 100))
            await asyncio.sleep(random.uniform(0.3, 0.6))
```

### 4.3 Page Interaction Sequence

```python
async def interact_like_human(page):
    """Simulate human browsing before extracting data."""
    # 1. Wait after page load (reading time)
    await asyncio.sleep(random.uniform(0.5, 1.5))

    # 2. Move mouse to neutral area
    await human_mouse_move(page, random.randint(300, 600), random.randint(200, 400))

    # 3. Scroll down slowly
    await human_scroll(page)

    # 4. Move mouse near price area
    price_elem = await page.query_selector('[data-asin-price], .a-price')
    if price_elem:
        box = await price_elem.bounding_box()
        if box:
            await human_mouse_move(page, box['x'] + box['width']/2, box['y'] + box['height']/2)

    # 5. Brief pause before extraction
    await asyncio.sleep(random.uniform(0.3, 0.7))
```

### 4.4 Timing Variance

All delays use natural variance:

```python
def human_delay(base_ms: int, variance_pct: float = 0.3) -> float:
    """Generate human-like delay with variance."""
    variance = base_ms * variance_pct
    delay_ms = base_ms + random.uniform(-variance, variance)
    return delay_ms / 1000  # Return seconds
```

### 4.5 Cookie Banner Handling

```python
COOKIE_ACCEPT_SELECTORS = [
    "#sp-cc-accept",
    "[data-cel-widget='sp-cc-accept']",
    "input[data-action-type='DISMISS']",
]

async def handle_cookie_banner(page):
    """Accept cookie banner if present."""
    for selector in COOKIE_ACCEPT_SELECTORS:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                await asyncio.sleep(random.uniform(0.3, 0.8))
                await elem.click()
                await asyncio.sleep(random.uniform(0.2, 0.5))
                return True
        except:
            continue
    return False
```

---

## 5. Request Strategy Layer

Manage *when* and *how often* to make requests.

### 5.1 Identity Manager

```python
class IdentityManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.identities = [BrowserIdentity(**p) for p in IDENTITY_PROFILES]

    def get_healthy_identity(self) -> Optional[BrowserIdentity]:
        """Get a healthy identity with lowest usage."""
        now = datetime.now(timezone.utc)
        healthy = [
            i for i in self.identities
            if not i.burned_until or i.burned_until < now
        ]

        if not healthy:
            return None

        # Sort by request count, pick lowest
        healthy.sort(key=lambda i: self._get_request_count(i.id))
        return healthy[0]

    def mark_success(self, identity: BrowserIdentity):
        count = self._increment_request_count(identity.id)
        if count >= random.randint(10, 20):
            self._reset_request_count(identity.id)
            self._rotate_cookies(identity.id)

    def mark_burned(self, identity: BrowserIdentity):
        burn_until = datetime.now(timezone.utc) + timedelta(hours=24)
        self.redis.set(f"amazon:identity:{identity.id}:burned", burn_until.isoformat())
        identity.burned_until = burn_until
```

### 5.2 Request Timing

```python
AMAZON_MIN_DELAY = 5  # Minimum seconds between any Amazon requests
AMAZON_PREFERRED_HOURS = range(2, 7)  # 2-6 AM EST

async def should_fetch_now() -> bool:
    """Check if we should make an Amazon request now."""
    # Check rate limit
    last_request = redis.get("amazon:last_request")
    if last_request:
        elapsed = time.time() - float(last_request)
        if elapsed < AMAZON_MIN_DELAY:
            return False

    return True

def record_request():
    """Record that we made a request."""
    redis.set("amazon:last_request", time.time())
```

### 5.3 Failure Classification & Handling

```python
class AmazonFailureType(Enum):
    CAPTCHA = "captcha"
    RATE_LIMITED = "rate_limited"
    NO_PRICE_FOUND = "no_price"
    NETWORK_ERROR = "network"

def classify_failure(page_content: str, status_code: int) -> AmazonFailureType:
    content_lower = page_content.lower()

    if 'captcha' in content_lower or 'robot check' in content_lower:
        return AmazonFailureType.CAPTCHA
    if status_code in (429, 503):
        return AmazonFailureType.RATE_LIMITED
    if status_code == 200:
        return AmazonFailureType.NO_PRICE_FOUND
    return AmazonFailureType.NETWORK_ERROR

async def handle_failure(failure_type: AmazonFailureType, identity: BrowserIdentity, manager: IdentityManager):
    if failure_type == AmazonFailureType.CAPTCHA:
        manager.mark_burned(identity)
        # Could retry with different identity
    elif failure_type == AmazonFailureType.RATE_LIMITED:
        await asyncio.sleep(300)  # Back off 5 minutes
    # NO_PRICE_FOUND and NETWORK_ERROR: log but don't burn identity
```

### 5.4 Graceful Degradation

- If all identities burned: skip Amazon items for 24h, log alert
- If success rate drops below 20% over 1 hour: pause and alert
- Always update `price_updated_at` even on failure to prevent retry storms

---

## 6. Implementation

### 6.1 New Files

```
services/
├── amazon_stealth/
│   ├── __init__.py
│   ├── identities.py       # BrowserIdentity dataclass, IDENTITY_PROFILES
│   ├── identity_manager.py # IdentityManager class, Redis persistence
│   ├── behaviors.py        # human_mouse_move, human_scroll, etc.
│   └── extractor.py        # stealth_fetch_amazon() main function
```

### 6.2 Modified Files

**services/price_service.py:**
```python
def _fetch_amazon_price(url):
    # 1. Check cache (existing)
    cached = price_cache.get_cached_response(url)
    if cached:
        return _extract_amazon_price_from_soup(BeautifulSoup(cached, 'html.parser'))

    # 2. Try stealth Playwright
    from services.amazon_stealth import stealth_fetch_amazon, identity_manager

    identity = identity_manager.get_healthy_identity()
    if identity:
        result = stealth_fetch_amazon(url, identity)
        if result.success:
            return result.price

    # 3. All identities exhausted
    logger.warning(f"All Amazon identities exhausted, skipping {url}")
    return None
```

**requirements.txt:**
```
playwright-stealth>=1.0.0
```

### 6.3 Redis Keys

```
amazon:identity:{id}:requests  → int (request count today, TTL 24h)
amazon:identity:{id}:burned    → ISO timestamp (if burned)
amazon:identity:{id}:cookies   → serialized cookie jar
amazon:last_request            → Unix timestamp (rate limiting)
amazon:health:success_count    → int (rolling 1h window)
amazon:health:total_count      → int (rolling 1h window)
```

### 6.4 Main Extractor Function

```python
async def stealth_fetch_amazon(url: str, identity: BrowserIdentity) -> ExtractionResult:
    """Fetch Amazon price using full stealth mode."""
    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent=identity.user_agent,
            viewport=identity.viewport,
            locale=identity.locale,
            timezone_id=identity.timezone,
            color_scheme=identity.color_scheme,
            device_scale_factor=identity.device_scale,
        )

        # Apply stealth patches
        page = await context.new_page()
        await stealth_async(page)

        # Load cookies if available
        cookies = load_cookies(identity.id)
        if cookies:
            await context.add_cookies(cookies)

        try:
            # Navigate with timeout
            await page.goto(url, timeout=30000, wait_until='domcontentloaded')

            # Handle cookie banner
            await handle_cookie_banner(page)

            # Human-like interaction
            await interact_like_human(page)

            # Check for CAPTCHA
            content = await page.content()
            if 'captcha' in content.lower() or 'robot check' in content.lower():
                return ExtractionResult(success=False, failure_type=AmazonFailureType.CAPTCHA)

            # Extract price
            soup = BeautifulSoup(content, 'html.parser')
            price = _extract_amazon_price_from_soup(soup)

            # Save cookies for next time
            cookies = await context.cookies()
            save_cookies(identity.id, cookies)

            # Cache the content
            if price:
                price_cache.cache_response(url, content)

            return ExtractionResult(success=price is not None, price=price)

        except Exception as e:
            logger.error(f"Stealth fetch failed: {e}")
            return ExtractionResult(success=False, failure_type=AmazonFailureType.NETWORK_ERROR)

        finally:
            await browser.close()
```

---

## 7. Testing Strategy

### 7.1 Unit Tests (Mocked)

- Identity rotation logic
- Burn/cooldown tracking
- Failure classification
- Cookie persistence serialization

### 7.2 Integration Tests (Manual)

- Test against 5-10 real Amazon URLs manually
- Run in isolation, not CI (avoid burning IPs)
- Track success/failure for baseline comparison

### 7.3 Staged Rollout

1. Deploy with feature flag (`AMAZON_STEALTH_ENABLED=false`)
2. Enable for 10% of Amazon requests
3. Monitor success rate vs old approach
4. Gradually increase to 100% if metrics improve

---

## 8. Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Amazon success rate | ~10% | 50-60% | `PriceExtractionLog` where domain contains 'amazon' |
| CAPTCHA rate | Unknown | <30% | New `failure_type` field in extraction log |
| Avg extraction time | ~8s | <12s | Acceptable increase for stealth overhead |
| Identity burn rate | N/A | <2/day | Redis tracking |

### Monitoring Query

```sql
SELECT
    DATE(created_at) as day,
    COUNT(*) as attempts,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
    ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate,
    SUM(CASE WHEN error_type = 'captcha' THEN 1 ELSE 0 END) as captchas
FROM price_extraction_log
WHERE domain LIKE '%amazon%'
GROUP BY DATE(created_at)
ORDER BY day DESC
LIMIT 14;
```

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Amazon updates detection | Stealth stops working | Monitor success rate, alert on drops, keep stealth lib updated |
| All identities burned | No Amazon prices for 24h | 10-15 identities, conservative rotation, graceful skip |
| Heroku IP blacklisted | All requests blocked | Unlikely with low volume; self-hosting fallback option |
| Playwright resource usage | Higher Heroku costs | Limit concurrent stealth fetches, prefer cache |
| Complexity maintenance | Hard to debug | Good logging, clear separation of concerns |

---

## 10. Estimated Effort

| Task | Hours |
|------|-------|
| Identity profiles & manager | 2-3 |
| Behavior functions (mouse, scroll) | 2-3 |
| Main stealth extractor | 2-3 |
| Integration with price_service | 1-2 |
| Testing & tuning | 2-3 |
| **Total** | **8-12** |

---

## 11. Future Enhancements (Out of Scope)

- Residential proxy integration (if free option insufficient)
- CAPTCHA solving service integration
- Machine learning for optimal timing
- Browser extension fallback for manual capture
