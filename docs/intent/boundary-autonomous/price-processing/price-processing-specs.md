# EARS Specifications: Price Processing

- [ ] **AUTO-PRC-001**: While processing async price batches, if the system encounters an Amazon URL, it shall process the Amazon requests sequentially (one at a time) to prevent memory exhaustion, while processing non-Amazon URLs concurrently (up to 5 at a time).
- [ ] **AUTO-PRC-002**: When the system fetches a new price, it shall record the new price in `PriceHistory` if the price changed by more than $0.01, or if it has been more than 6 hours since the last record.
- [ ] **AUTO-PRC-003**: When a price drops by 10% or more compared to its old price, the system shall generate a Notification for the item owner.
- [ ] **AUTO-PRC-004**: When a price drops by 10% or more, if the item is `Claimed` or `Purchased` by a user other than the owner, the system shall generate an additional Notification for the claimer.
- [ ] **AUTO-PRC-005**: If the `AMAZON_STEALTH_ENABLED` flag is true, the system shall attempt to fetch Amazon prices using the identity manager and headless browser stealth mode before falling back to legacy extraction.
- [x] **AUTO-PRC-006**: When `update_stale_prices` executes, it shall identify items whose `price_updated_at` is older than 7 days, or is null, and attempt to fetch updated prices for them.
- [x] **AUTO-PRC-007**: If an item's URL price fetch fails during a batch update, the system shall stamp the item's `price_updated_at` to approximately 6 days old (retry pacing) so the item crosses the 7-day staleness window again in about a day — failed URLs retry ~daily instead of being treated as freshly updated (full 7-day wait) or hammered on subsequent immediate runs.
- [x] **AUTO-PRC-009**: When `update_stale_prices` processes a batch of URLs, it shall process them in chunks of 25 and commit each chunk to the database as it completes, so completed chunks survive a task time-limit kill instead of being lost to a single final commit.
- [ ] **AUTO-PRC-008**: When fetching metadata via the generic fallback, the system shall prioritize extracting data from `og:*` metadata tags (e.g., `og:price:amount`, `og:image`) before falling back to HTML parsing.
