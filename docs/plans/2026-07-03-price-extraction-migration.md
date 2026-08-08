# Price-Extraction Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `services/price_extraction/` the single source of truth for price parsing, delete the ~700 duplicated extractor lines from `services/price_service.py`, and mechanically deduplicate `blueprints/items.py` — with zero behavior change.

**Architecture:** `price_service.py` keeps all *fetching* concerns (requests sessions, retries, response cache, Playwright fallback, Amazon stealth orchestration) and delegates all *parsing* to the extractor registry in `services/price_extraction/extractors/`. `price_async.py` and `amazon_stealth/extractor.py` switch from poking `price_service` privates to calling the same registry.

**Tech Stack:** Flask, BeautifulSoup, pytest. Test runner: `.venv/bin/python -m pytest` (venv is `.venv`, managed by uv — NOT `venv/`).

**Spec:** `docs/plans/2026-07-03-price-extraction-migration-design.md`

**Baseline (verified 2026-07-03):** `.venv/bin/python -m pytest tests/unit/ -q -p no:cacheprovider --no-cov` → 442 passed, 3 failed. The 3 failures are all in `tests/unit/test_price_extraction.py` and are fixed by Task 1. The unit-only run does NOT meet the 90% coverage gate (browser tests supply the rest), hence `--no-cov` for iteration.

---

### Task 1: Fix the 3 failing tests in the parser

**Files:**
- Modify: `services/price_extraction/parser.py`
- Test (existing, currently failing): `tests/unit/test_price_extraction.py`

- [x] **Step 1: Run the failing tests to confirm the failures**

Run:
```bash
.venv/bin/python -m pytest tests/unit/test_price_extraction.py::TestParsePrice::test_parse_price_negative tests/unit/test_price_extraction.py::TestUrlMatchers::test_url_matcher_empty tests/unit/test_price_extraction.py::TestUrlMatchers::test_url_matcher_none -p no:cacheprovider --no-cov -q
```
Expected: 3 failed — `parse_price('-$10.00')` returns `10.0` (want `None`); `is_amazon_url('')` and `is_amazon_url(None)` return `None` (want `False`).

- [x] **Step 2: Fix `parse_price` to reject negative prices**

In `services/price_extraction/parser.py`, immediately after `price_text = str(price_text).strip()` (line 29), add:

```python
    # Negative values are not valid prices (e.g. "-$10.00")
    if price_text.startswith('-'):
        return None
```

(This sits BEFORE the range-split block. Ranges like `"$10 - $20"` are unaffected because they don't start with `-`.)

- [x] **Step 3: Fix the five `is_*_url` matchers to return real booleans**

In the same file, wrap each matcher's return expression in `bool(...)`. All five follow the same pattern; here is each complete function body:

```python
def is_amazon_url(url):
    """Check if URL is an Amazon product page."""
    domain = get_domain(url)
    return bool(domain and ('amazon.com' in domain or 'amazon.' in domain))


def is_walmart_url(url):
    """Check if URL is a Walmart product page."""
    domain = get_domain(url)
    return bool(domain and 'walmart.com' in domain)


def is_target_url(url):
    """Check if URL is a Target product page."""
    domain = get_domain(url)
    return bool(domain and 'target.com' in domain)


def is_bestbuy_url(url):
    """Check if URL is a Best Buy product page."""
    domain = get_domain(url)
    return bool(domain and 'bestbuy.com' in domain)


def is_etsy_url(url):
    """Check if URL is an Etsy product page."""
    domain = get_domain(url)
    return bool(domain and 'etsy.com' in domain)
```

- [x] **Step 4: Run the whole price_extraction test file**

Run: `.venv/bin/python -m pytest tests/unit/test_price_extraction.py -p no:cacheprovider --no-cov -q`
Expected: all pass, 0 failed.

- [x] **Step 5: Commit**

```bash
git add services/price_extraction/parser.py
git commit -m "Fix parse_price negative handling and is_*_url bool coercion"
```

---

### Task 2: Flip `price_extraction/__init__.py` to export its own API

Currently `services/price_extraction/__init__.py` imports FROM `price_service` (backwards-compat re-exports). Once `price_service` imports the extractors (Task 3), that becomes a circular import. Nothing in the app imports these re-exports (verified by grep — only tests import submodules directly), so the flip is safe.

**Files:**
- Modify: `services/price_extraction/__init__.py` (full rewrite)

- [x] **Step 1: Replace the file contents entirely**

```python
"""Price extraction package: pluggable per-site price and metadata extractors.

Parsing lives here; fetching (sessions, retries, caching, Playwright,
Amazon stealth) lives in services.price_service, which delegates to the
extractor registry below.
"""

from services.price_extraction.extractors import (
    BasePriceExtractor,
    AmazonPriceExtractor,
    BestBuyPriceExtractor,
    EtsyPriceExtractor,
    GenericPriceExtractor,
    TargetPriceExtractor,
    WalmartPriceExtractor,
    EXTRACTORS,
    get_extractor_for_url,
)
from services.price_extraction.parser import parse_price, get_domain

__all__ = [
    'BasePriceExtractor',
    'AmazonPriceExtractor',
    'BestBuyPriceExtractor',
    'EtsyPriceExtractor',
    'GenericPriceExtractor',
    'TargetPriceExtractor',
    'WalmartPriceExtractor',
    'EXTRACTORS',
    'get_extractor_for_url',
    'parse_price',
    'get_domain',
]
```

- [x] **Step 2: Run the unit suite to confirm nothing depended on the re-exports**

Run: `.venv/bin/python -m pytest tests/unit/ -p no:cacheprovider --no-cov -q`
Expected: same pass count as baseline (445 passed after Task 1), 0 failed.

- [x] **Step 3: Commit**

```bash
git add services/price_extraction/__init__.py
git commit -m "Export price_extraction's own API instead of re-exporting price_service"
```

---

### Task 3: Delegate all price parsing in `price_service.py` to the extractors

This is the core task. `fetch_price`'s public behavior is unchanged; internally, per-site parsing is replaced by the extractor registry. Site-specific *fetch* quirks stay (Amazon headers + stealth + CAPTCHA→Playwright, Target Playwright fallback).

**Files:**
- Modify: `services/price_service.py`
- Modify: `services/price_async.py:278-326` (`_parse_content`)
- Modify: `services/amazon_stealth/extractor.py:143-146`
- Modify: `tests/unit/test_price_service.py:32-56` (parse-price tests)
- Modify: `tests/unit/test_price_crawler_v2.py:57,74` (patch targets)

- [x] **Step 1: Add extractor imports to `price_service.py`**

Near the top, after `from services import price_cache, price_metrics`, add:

```python
from services.price_extraction.extractors import (
    get_extractor_for_url,
    AmazonPriceExtractor,
    GenericPriceExtractor,
    TargetPriceExtractor,
)
```

- [x] **Step 2: Rewrite `fetch_price`'s dispatch to three branches**

Inside `fetch_price`, replace the six-way `if/elif` dispatch (lines 140-153 of the current file) with:

```python
        # Amazon and Target need special fetching (stealth / Playwright fallback);
        # everything else is fetch-then-extract with the registry.
        if 'amazon' in domain or domain in ['a.co', 'amzn.to', 'amzn.eu']:
            price = _fetch_amazon_price(url)
        elif 'target.com' in domain:
            price = _fetch_target_price(url)
        else:
            price = _fetch_standard_price(url)
```

- [x] **Step 3: Add `_fetch_standard_price` (replaces the Walmart/BestBuy/Etsy/generic fetchers)**

```python
def _fetch_standard_price(url):
    """Fetch a page and extract its price with the site-appropriate extractor."""
    try:
        response = _make_request(url)
        if not response:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        return get_extractor_for_url(url).extract_from_soup(soup)
    except Exception as e:
        logger.warning(f'Price fetch failed for {url}: {str(e)}')
        return None
```

- [x] **Step 4: Rewrite `_fetch_amazon_price_legacy` to delegate parsing**

`_fetch_amazon_price` (the stealth orchestrator) is UNCHANGED. Replace `_fetch_amazon_price_legacy` with:

```python
def _fetch_amazon_price_legacy(url):
    """Legacy Amazon extraction: requests first, Playwright on CAPTCHA.

    Note: Amazon actively blocks scraping. This may fail due to CAPTCHAs,
    bot detection, or page structure changes. For reliable Amazon pricing,
    consider the Amazon Product Advertising API.
    """
    try:
        session = _get_session()
        session.headers.update({
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.amazon.com/',
            'DNT': '1',
        })

        response = _make_request(url, session)
        if not response:
            logger.warning(f'Amazon request failed (possible bot detection): {url}')
            return None

        extractor = AmazonPriceExtractor()
        if 'captcha' in response.text.lower() or 'robot check' in response.text.lower():
            logger.warning(f'Amazon returned CAPTCHA/robot check page via requests, trying Playwright: {url}')
            soup = _fetch_with_playwright(url)
            if soup:
                return extractor.extract_from_soup(soup)
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        return extractor.extract_from_soup(soup)
    except Exception as e:
        logger.warning(f'Amazon price fetch failed for {url}: {str(e)}')
        return None
```

- [x] **Step 5: Rewrite `_fetch_target_price` to delegate parsing**

```python
def _fetch_target_price(url):
    """Fetch price from Target, falling back to Playwright for JS-rendered pages."""
    extractor = TargetPriceExtractor()
    try:
        response = _make_request(url)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string if soup.title and soup.title.string else ''
            if 'Access Denied' in title:
                logger.warning(f'Target blocked requests for {url}')
            else:
                price = extractor.extract_from_soup(soup)
                if price:
                    return price

        logger.info(f'Trying Target fallback via Playwright for {url}')
        soup = _fetch_with_playwright(url)
        if soup:
            return extractor.extract_from_soup(soup)
        return None
    except Exception as e:
        logger.warning(f'Target price fetch failed for {url}: {str(e)}')
        return None
```

(The old code's `if "Access Denied" in soup.title.string if soup.title else "":` was a
buggy conditional expression that could raise `TypeError` on a title-less page and skip
the Playwright fallback; the rewrite preserves the intended behavior.)

- [x] **Step 6: Rewrite `_fetch_amazon_metadata` to delegate, preserving the `image_url` key**

```python
def _fetch_amazon_metadata(url):
    """Fetch all metadata from Amazon."""
    try:
        session = _get_session()
        session.headers.update({
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.amazon.com/',
            'DNT': '1',
        })
        response = _make_request(url, session)

        if response and 'captcha' not in response.text.lower() and 'robot check' not in response.text.lower():
            soup = BeautifulSoup(response.text, 'html.parser')
        else:
            logger.warning(f'Amazon CAPTCHA detected, switching to Playwright for metadata: {url}')
            soup = _fetch_with_playwright(url)

        if not soup:
            return {}

        data = AmazonPriceExtractor().extract_metadata(soup)
        # The extractor uses 'image'; the public fetch_metadata() contract uses 'image_url'.
        metadata = {}
        if data.get('title'):
            metadata['title'] = data['title']
        if data.get('price'):
            metadata['price'] = data['price']
        if data.get('image'):
            metadata['image_url'] = data['image']
        return metadata

    except Exception as e:
        logger.warning(f'Error fetching Amazon metadata: {e}')
        return {}
```

- [x] **Step 7: Simplify `_fetch_generic_metadata`'s price fallback**

Keep the function and its OpenGraph/title/twitter-image handling as-is, but replace the
entire "3. Price Fallback" block (the microdata check plus the `price_classes` loop,
currently lines 950-973) with:

```python
        # 3. Price Fallback
        if not metadata.get('price'):
            price = GenericPriceExtractor().extract_from_soup(soup)
            if price:
                metadata['price'] = price
```

(GenericPriceExtractor tries meta tags → JSON-LD → microdata → CSS classes, a superset
of the old fallback chain and identical to what `fetch_price` uses for generic sites.)

- [x] **Step 8: Delete the now-dead parsing code from `price_service.py`**

Delete these functions entirely:
- `_extract_amazon_price_from_soup`
- `_extract_amazon_price_from_scripts`
- `_fetch_target_price`'s old body (replaced in Step 5) and `_extract_target_price_from_soup`
- `_fetch_walmart_price`, `_extract_walmart_price_from_soup`
- `_fetch_bestbuy_price`, `_extract_bestbuy_price_from_soup`
- `_fetch_etsy_price`, `_extract_etsy_price_from_soup`
- `_fetch_generic_price`, `_extract_generic_price_from_soup`
- `_extract_price_from_json_ld_all`, `_extract_price_from_json_ld`
- `_deep_search_dict`
- `_parse_price`

- [x] **Step 9: Repoint `services/amazon_stealth/extractor.py`**

At lines 143-146, replace:

```python
            # Extract price using existing logic
            from services.price_service import _extract_amazon_price_from_soup
            soup = BeautifulSoup(content, 'html.parser')
            price = _extract_amazon_price_from_soup(soup)
```

with:

```python
            # Extract price using the shared Amazon extractor
            from services.price_extraction.extractors import AmazonPriceExtractor
            soup = BeautifulSoup(content, 'html.parser')
            price = AmazonPriceExtractor().extract_from_soup(soup)
```

- [x] **Step 10: Replace `price_async._parse_content`**

Replace the whole function (lines 278-326) with:

```python
def _parse_content(url: str, html_content: str) -> Optional[float]:
    """Parse price from HTML content using the site-appropriate extractor."""
    try:
        from services.price_extraction.extractors import get_extractor_for_url
        soup = BeautifulSoup(html_content, 'html.parser')
        return get_extractor_for_url(url).extract_from_soup(soup)
    except Exception as e:
        logger.error(f"Parsing failed for {url}: {e}")
        return None
```

- [x] **Step 11: Repoint tests that referenced deleted internals**

In `tests/unit/test_price_service.py`, the five parse-price tests (lines 32-56) import
`_parse_price` from `services.price_service`. Change each import to:

```python
        from services.price_extraction.parser import parse_price as _parse_price
```

(Keeping the `_parse_price` alias means the assertion lines don't change.)

In `tests/unit/test_price_crawler_v2.py` lines 57 and 74, change the patch target:

```python
# before
with patch('services.price_service._fetch_generic_price', return_value=99.99):
# after
with patch('services.price_service._fetch_standard_price', return_value=99.99):
```

(same substitution on line 74 with `side_effect=ValueError("Parse Error")`).

`tests/unit/test_amazon_stealth_integration.py` needs NO changes — `_fetch_amazon_price`,
`_fetch_amazon_price_legacy`, and `_make_request` all still exist.

- [x] **Step 12: Run the unit suite**

Run: `.venv/bin/python -m pytest tests/unit/ -p no:cacheprovider --no-cov -q`
Expected: 445 passed, 0 failed. If an Amazon/Target/Walmart extraction test fails,
diff the failing extractor against the legacy function in `git show HEAD:services/price_service.py`
and port the missing selector/strategy into the extractor — do NOT resurrect the legacy function.

- [x] **Step 13: Commit**

```bash
git add services/price_service.py services/price_async.py services/amazon_stealth/extractor.py tests/unit/test_price_service.py tests/unit/test_price_crawler_v2.py
git commit -m "Delegate price parsing to price_extraction extractors, delete duplicates"
```

---

### Task 4: Mechanical dedup in `blueprints/items.py`

Zero behavior change: no route URLs, template context keys, flash messages, or status
codes change. Existing route tests are the safety net.

**Files:**
- Modify: `blueprints/items.py`

- [x] **Step 1: Add module-level constant and helpers (after the `bp = Blueprint(...)` line)**

```python
DEFAULT_IMAGE_URL = 'https://via.placeholder.com/600x400?text=Wishlist+Item'


def _get_item_or_404(item_id):
    """Fetch an item by id or abort with 404."""
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)
    return item


def _item_card_response(item, message, category):
    """Render the htmx partial response for claim/unclaim actions.

    Dashboard context gets the compact card plus rendered flash messages;
    the items page gets the full card (flash intentionally omitted there).
    """
    if request.args.get('context') == 'dashboard':
        flash(message, category)
        card_html = render_template('partials/_dashboard_item_card.html', item=item)
        flash_html = render_template('partials/_flash_messages.html')
        return card_html + flash_html
    return render_template('partials/_item_card.html', item=item, default_image_url=DEFAULT_IMAGE_URL)


def _parse_contribution_amount():
    """Parse and validate the split contribution amount from the form.

    Returns (amount, error_response); exactly one is None.
    """
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        flash('Invalid contribution amount.', 'danger')
        return None, redirect(get_items_url_with_filters())
    if amount <= 0:
        flash('Contribution amount must be positive.', 'danger')
        return None, redirect(get_items_url_with_filters())
    return amount, None
```

- [x] **Step 2: Replace the five `default_image_url = 'https://via.placeholder.com/...'` literals**

In `items_list`, `claim_item`, `unclaim_item`, `get_split_modal`, and `my_claims`,
delete the local `default_image_url = '...'` assignment and pass
`default_image_url=DEFAULT_IMAGE_URL` (or use the constant directly) instead.

- [x] **Step 3: Replace the get-or-404 pattern with `_get_item_or_404`**

In these nine routes, replace the two/three-line `item = db.session.get(Item, item_id)` +
`if item is None: abort(404)` (or `if not item: abort(404)`) block with
`item = _get_item_or_404(item_id)`:
`edit_item`, `claim_item`, `unclaim_item`, `get_split_modal`, `refresh_price`,
`start_split`, `join_split`, `withdraw_contribution`, `complete_split`.

Do NOT change `get_item_modal` (returns a plain-text 404, not the error page) or
`delete_item` (combines the not-found and not-owner cases into one flash+redirect).

- [x] **Step 4: Use `_item_card_response` in `claim_item` and `unclaim_item`**

In `claim_item`, the htmx block becomes:

```python
    if request.headers.get('HX-Request'):
        return _item_card_response(item, f'You have claimed "{item.description}".', 'success')

    flash(f'You have claimed "{item.description}".', 'success')
    return redirect(get_items_url_with_filters())
```

In `unclaim_item`, the corresponding block inside the `if item.status == 'Claimed' and ...` branch becomes:

```python
        if request.headers.get('HX-Request'):
            return _item_card_response(item, f'You have unclaimed "{item.description}".', 'info')

        flash(f'You have unclaimed "{item.description}".', 'info')
```

(The trailing `else: flash('You cannot unclaim this item.', 'danger')` and final
`return redirect(...)` stay exactly as they are.)

- [x] **Step 5: Use `_parse_contribution_amount` in the two split routes**

In `start_split` and `join_split`, replace the try/except float parse + `amount <= 0`
check (two blocks of ~10 lines each) with:

```python
    amount, error = _parse_contribution_amount()
    if error:
        return error
```

- [x] **Step 6: Run the items and split test files, then the whole unit suite**

Run: `.venv/bin/python -m pytest tests/unit/ -p no:cacheprovider --no-cov -q`
Expected: 445 passed, 0 failed.

- [x] **Step 7: Commit**

```bash
git add blueprints/items.py
git commit -m "Deduplicate items blueprint: shared 404/card/amount helpers"
```

---

### Task 5: Full-suite verification

- [x] **Step 1: Run the complete test suite (unit + browser) with coverage**

Browser tests need Playwright browsers: if `tests/browser` fails at startup with a
missing-executable error, run `.venv/bin/playwright install chromium` first.

Run: `.venv/bin/python -m pytest -p no:cacheprovider`
Expected: all tests pass; coverage gate (90%) met. Takes ~6-8 minutes.

If browser tests cannot run locally (missing system deps), run
`.venv/bin/python -m pytest tests/unit/ -p no:cacheprovider --no-cov -q` (expected:
445 passed) and note that CI must run the full suite.

- [x] **Step 2: Confirm the line-count payoff**

Run: `wc -l services/price_service.py blueprints/items.py`
Expected: `price_service.py` ≈ 450-550 lines (from 1,201); `items.py` ≈ 570-600 (from 641).

- [x] **Step 3: Final commit if anything was adjusted during verification**

```bash
git status  # should be clean of *new* changes from this plan; pre-existing pending refactor files remain
```
