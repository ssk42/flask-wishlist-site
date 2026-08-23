# Low-Level Design (LLD): Price Processing

## 1. Segment Overview
This segment handles external price extraction and metadata fetching for product URLs, integrating with third-party sites while overcoming bot-protection (e.g., CAPTCHA). It also governs the autonomous scheduling of price refreshes for stale items and maintains a history of price changes.

## 2. Component Architecture
- **Price Service (`services/price_service.py`)**: Central coordinator for synchronous price and metadata extraction. Triggers site-specific extractors and handles caching/retries.
- **Async Price Fetcher (`services/price_async.py`)**: Processes batch URL fetches concurrently using `aiohttp`, optimizing for background jobs.
- **Price History & Metrics (`services/price_history.py`, `services/price_metrics.py`)**: Records price changes (conditionally based on time or value thresholds) and extraction telemetry (success/failure rates, latencies).
- **Extraction Engines (`services/price_extraction/*`)**: Site-specific HTML parsers. Includes a generic fallback using OpenGraph tags.
- **Amazon Stealth (`services/amazon_stealth/*`)**: [inferred] Uses a pool of rotated browser identities via Playwright to bypass Amazon bot protections. Burns identities that hit CAPTCHAs.

## 3. Data & State Management
- **Price Staleness**: Items are considered stale if their `price_updated_at` timestamp is older than 7 days (or null).
- **Price History Constraints**: A new price point is only appended if the difference from the last recorded price is > $0.01, OR if the last record is > 6 hours old (heartbeat).
- **Identity Manager State**: [inferred] Tracks active, burned, and resting browser identities via Redis for Amazon Stealth.

## 4. Workflows

### 4.1. Batch Price Updating
1. `update_stale_prices` identifies stale items.
2. URLs are aggregated and passed to `fetch_prices_batch` **in chunks of 25**, committing each chunk to the database as it completes (long sweeps can outlast a Celery task's time limit; per-chunk commits mean completed chunks survive a hard kill).
3. Standard URLs are processed concurrently via a semaphore (limit: 5).
4. Amazon URLs are processed *sequentially* (one-by-one) via stealth mode to avoid memory exhaustion from multiple concurrent Playwright instances.
5. Successfully fetched prices trigger history updates and stamp the item as freshly updated.
6. Significant price drops (>= 10%) generate notifications for the owner and (if applicable) the claimer.
7. **Failed fetches are retry-paced**: `price_updated_at` is stamped ~6 days old so the item crosses the 7-day staleness window again in about a day, letting the next cycle retry it without hammering it immediately.
8. **Browser rescue**: after the aiohttp phase, any non-Amazon URL that failed with HTTP 403/429 *or* returned 200 with no parseable price (JS-rendered, e.g. Target) is retried through the headless browser (stealth + rotated identity, sequential to bound memory), parsed with the site-appropriate extractor. Network errors are not rescued. No-price responses are not cached. Gated by `BROWSER_RESCUE_ENABLED`.

### 4.2. Stealth Extraction (Amazon)
1. Requests an identity from `IdentityManager`.
2. Spawns an async Playwright browser.
3. If successful, updates the item and marks the identity as successful.
4. If a CAPTCHA is hit, marks the identity as burned and returns `None` (falling back or skipping).

### 4.3. Price-Fetch Backoff Circuit Breaker
Persistently unpriceable URLs stop consuming a daily retry slot without being permanently shelved. Two new nullable/defaulted columns on `Item` (models.py):
- `price_fail_streak` INT NOT NULL DEFAULT 0
- `price_backoff_until` DATETIME NULL

**Failure accounting** — on a FAILED automatic price attempt (`update_stale_prices`, the same path where AUTO-PRC-007 stamps `price_updated_at` ~6d old): increment `price_fail_streak`. IF the new streak >= the backoff floor (`PRICE_BACKOFF_FLOOR`, default 3): also set `price_backoff_until = now + min(2 × 2**(streak − floor) days, PRICE_BACKOFF_MAX_DAYS)`. Below the floor, no `price_backoff_until` is set — today's ~daily retry pacing (AUTO-PRC-007) is preserved.

Backoff schedule (default floor 3, default max 30 days):

| Consecutive failures | Automatic retry pacing |
|---|---|
| 1–2 | unchanged (~daily via the AUTO-PRC-007 stamp), no backoff |
| 3 | +2 days |
| 4 | +4 days |
| 5 | +8 days |
| 6 | +16 days |
| >=7 | +30 days (cap, `PRICE_BACKOFF_MAX_DAYS`) |

**Sweep exclusion** — `get_items_needing_update` additionally requires `(price_backoff_until IS NULL OR price_backoff_until <= now)`. Backed-off items are skipped by the sweep and become automatically eligible again once their backoff expires — self-healing; nothing is permanently shelved.

**Reset on success** — any successful price fetch (batch chunk path or `refresh_item_price`) resets both fields: `price_fail_streak = 0` AND `price_backoff_until = NULL`.

**Link change resets both** — via ONE choke point: a SQLAlchemy `before_flush` event listener that detects a dirty `item.link` change and clears both fields. The listener is registered where other model events/extensions initialize (app factory), so every write path (web `edit_item`, api_v1 PATCH, scripts) is caught without editing blueprints.

**Manual refresh bypasses backoff** — the `items.refresh_price` route calls `services.price_service.refresh_item_price(item, db)` directly: it always attempts the fetch regardless of `price_backoff_until`, resets both fields on success, and applies normal failure accounting otherwise.

**User-visible indication** — [D] deferred: a card badge showing that auto-pricing is paused is recorded in Open Questions and AUTO-PRC-017, not built with this behavior.

## 5. Open Questions, Quirks, & TODOs
- **Synchronous Event Loop Blocking**: [inferred] `price_async.py` writes metrics to the database using synchronous SQLAlchemy calls, which could block the async event loop under high concurrency.
- **Target Extraction Quirks**: Target extraction attempts standard `requests` first, and if the response title contains "Access Denied", it falls back to Playwright.
- **Amazon Legacy Fallback**: If Stealth is disabled or all identities are burned, it falls back to a legacy requests-based extraction which is highly prone to blocking.
- **watch.sh interplay (rollout step, not this segment)**: backed-off items freeze `price_updated_at`, so the hp-server `~/home-server/bin/watch.sh` "frozen>3d" nudge would fire forever for them. Its staleness query must eventually ignore backed-off items (`price_backoff_until IS NOT NULL OR price_fail_streak > 0`). Ship as a rollout step when this feature deploys.
- **User-visible paused indication**: a card badge (or equivalent) showing that automatic pricing is paused for an item is deferred — see AUTO-PRC-017 ([D]).

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| Explicit two-column state: `price_fail_streak` + capped `price_backoff_until`. | Deriving backoff state from `price_extraction_log` (no schema change). | Rejected: requires a per-item subquery over an ever-growing log on every sweep selection, and its semantics silently shift if log retention changes. Chosen design gives the sweep a free predicate and self-heals within 30 days worst case. |
| Same decision. | Backoff by deepening only the AUTO-PRC-007 failure stamp (`price_updated_at` pushed further back per failure). | Rejected: still needs stored streak state to know how deep to push, so it saves nothing, and it entangles retry pacing with circuit-breaking in one field. |
| Same decision. | Permanent hard exclusion at streak >= K (no retry probe). | Rejected: conflates permanently-unpriceable pages with temporarily bot-blocked ones; recovery after an egress fix would require a manual refresh for every affected item instead of happening automatically. |
