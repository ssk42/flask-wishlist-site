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
8. **Browser rescue**: after the aiohttp phase, any non-Amazon URL that failed with HTTP 403/429 is retried once through the headless browser (stealth + rotated identity, sequential to bound memory), parsed with the site-appropriate extractor. A 200-parse-miss or network error is not a bot block and is not rescued. Gated by `BROWSER_RESCUE_ENABLED`.

### 4.2. Stealth Extraction (Amazon)
1. Requests an identity from `IdentityManager`.
2. Spawns an async Playwright browser.
3. If successful, updates the item and marks the identity as successful.
4. If a CAPTCHA is hit, marks the identity as burned and returns `None` (falling back or skipping).

## 5. Open Questions, Quirks, & TODOs
- **Synchronous Event Loop Blocking**: [inferred] `price_async.py` writes metrics to the database using synchronous SQLAlchemy calls, which could block the async event loop under high concurrency.
- **Target Extraction Quirks**: Target extraction attempts standard `requests` first, and if the response title contains "Access Denied", it falls back to Playwright.
- **Amazon Legacy Fallback**: If Stealth is disabled or all identities are burned, it falls back to a legacy requests-based extraction which is highly prone to blocking.
