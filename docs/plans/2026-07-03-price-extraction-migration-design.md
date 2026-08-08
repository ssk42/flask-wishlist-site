# Design: Finish Price-Extraction Migration + items.py Dedup

**Date:** 2026-07-03
**Status:** Approved
**Goal:** No behavior change. One source of truth for price parsing. `services/price_service.py` drops from ~1,200 to ~450 lines.

## Background

The working tree contains an unfinished refactor: `services/price_extraction/` is a
clean, pluggable re-implementation of the six site-specific price extractors
(Amazon, Target, Walmart, Best Buy, Etsy, generic), with its own unit tests — but it
was never wired in. Its `__init__.py` re-exports the legacy functions from
`price_service.py`, nothing in the app imports its extractors, and 3 of its tests
fail. The codebase therefore carries two copies of every extractor: one live
(`price_service.py`), one dead-but-tested (`price_extraction/`).

`services/price_async.py::_parse_content` additionally reaches into
`price_service`'s private `_extract_*_from_soup` functions via `hasattr()` checks,
with a comment noting the ideal fix is exactly what `price_extraction` provides.

Verification baseline (2026-07-03): 442 unit tests pass; the only 3 failures are in
`tests/unit/test_price_extraction.py` (the unwired package's own tests).

## Part 1 — Fix the 3 failing tests in `price_extraction`

- `parser.py::parse_price`: `parse_price('-$10.00')` must return `None`. Detect a
  negative sign before symbol-stripping and reject.
- `parser.py::is_amazon_url` (and siblings): must return `False` for `''`/`None`,
  not `None`. Wrap the `domain and (...)` expression in `bool()`.

## Part 2 — Wire extraction through the extractors; delete the duplicates

**Stays in `price_service.py`** (fetching/orchestration concerns):
- `_get_session`, `_make_request`, `CachedResponse`, retry logic, response caching
- `_fetch_with_playwright` fallback
- Amazon stealth orchestration (`_get_identity_manager`, stealth branch, CAPTCHA
  detection and identity burning)
- `fetch_price`, `fetch_metadata` (public API — signatures and return shapes
  unchanged)
- `update_stale_prices`, `refresh_item_price`, `get_items_needing_update`,
  `_create_price_drop_notifications`

**Deleted from `price_service.py`** (~700 lines, replaced by delegation):
- `_fetch_amazon_price_legacy` parsing internals, `_extract_amazon_price_from_soup`,
  `_extract_amazon_price_from_scripts`
- `_fetch_target_price` / `_extract_target_price_from_soup` parsing internals
- `_fetch_walmart_price` / `_extract_walmart_price_from_soup` parsing internals
- `_fetch_bestbuy_price` / `_extract_bestbuy_price_from_soup` parsing internals
- `_fetch_etsy_price` / `_extract_etsy_price_from_soup` parsing internals
- `_fetch_generic_price` / `_extract_generic_price_from_soup` parsing internals
- `_parse_price`, `_extract_price_from_json_ld_all`, `_extract_price_from_json_ld`,
  `_deep_search_dict` (canonical versions live in `price_extraction`)

Delegation shape: fetch the response in `price_service` (keeping site-specific
fetch quirks — Amazon headers, CAPTCHA-to-Playwright fallback, Target Playwright
fallback), then call `get_extractor_for_url(url).extract_from_soup(soup)`.

**`price_async._parse_content`** becomes a call to the same extractor registry,
removing the `hasattr()` chain.

**Circular-import fix:** `price_extraction/__init__.py` currently imports *from*
`price_service`. That flips: the package exports its own API (extractors, parser,
fetcher helpers), and `price_service` imports from `price_extraction`.

**Parity requirements (checked before deleting each legacy extractor):**
- Diff each legacy extractor against its new counterpart; port any missing
  selectors/strategies into the new extractor.
- `fetch_metadata()` keeps its existing public dict shape (`image_url` key), even
  though the new extractors' `extract_metadata` uses `image`. Adapt at the boundary
  in `price_service`.
- Walmart `__NEXT_DATA__` deep-search logic must survive the migration.

**Test churn:** unit tests that monkeypatch or import `price_service._extract_*` /
`_parse_price` are repointed at the `price_extraction` equivalents. Assertions stay
behaviorally identical.

## Part 3 — Mechanical dedup in `blueprints/items.py` (~60 lines)

- `DEFAULT_IMAGE_URL` module constant (literal currently repeated 5×)
- `_get_item_or_404(item_id)` helper (get-or-404 pattern repeated ~10×; preserves
  the two routes that flash-and-redirect instead of 404)
- `_item_card_response(item)` helper for the duplicated htmx claim/unclaim block
- Shared contribution-amount parsing/validation for `start_split` / `join_split`

No route URLs, template context keys, flash messages, or status codes change.

## Testing / verification

- All 442 currently-passing unit tests stay green; the 3 `test_price_extraction`
  failures are fixed.
- Full unit suite run before and after; browser suite spot-checked if extraction
  paths are touched by it.
- `app.py` untouched (already lean at 185 lines).

## Out of scope

- No new features, no `items_list` query-builder restructuring, no template
  changes, no changes to the Amazon stealth module internals.
