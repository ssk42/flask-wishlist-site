# Implementation Plan: Price Crawler 2.0

**Status:** Phase 2 Complete
**PRD:** [docs/PRD_PRICE_CRAWLER.md](PRD_PRICE_CRAWLER.md)
**Start Date:** 2026-01-04

---

## Phase 1: Reliability & Monitoring (Current)

### 1.1 Redis Caching Layer
- [x] Create `services/price_cache.py`
  - [x] Implement `get_cached_response(url)`
  - [x] Implement `cache_response(url, content, ttl)`
  - [x] Handle Redis connection errors gracefully
- [x] Update `price_service.py` to use cache
  - [x] Wrap `_make_request` with cache logic

### 1.2 Extraction Logging (Database)
- [x] Update `models.py`
  - [x] Add `PriceExtractionLog` model
  - [x] Add indexes on `domain` and `created_at`
- [x] Generate DB Migration
  - [x] `flask db migrate -m "Add PriceExtractionLog model"`
  - [x] `flask db upgrade` (Applied locally)

### 1.3 Error Classification & Metrics
- [x] Create `services/price_metrics.py`
  - [x] Define `ExtractionError` Enum
  - [x] Implement `log_extraction_attempt` function
- [x] Update `price_service.py`
  - [x] Implement `_classify_error` (Basic implementation via Exception handling)
  - [x] Log every fetch attempt (success and failure)

### 1.4 Testing
- [x] Create `tests/unit/test_price_crawler_v2.py`
  - [x] Test caching logic (mock Redis)
  - [x] Test error classification
  - [x] Test logging

### 1.5 Monitoring
- [x] Add `/api/health/extraction` endpoint

---

## Phase 2: Performance (Next)

### 2.1 Async Batch Processing
- [x] Update `requirements.txt` (add `aiohttp`, `aiofiles`)
- [x] Create `services/price_async.py` (or similar)
  - [x] `fetch_prices_batch(urls)` implementation
  - [x] Cancellation/Timeout handling
- [x] Refactor `price_service.py` to expose parsers
- [x] Create `tests/unit/test_price_async.py` and verify

### 2.2 Smart Scheduling
- [x] Create scheduling logic
  - [x] `get_items_needing_update()` query extracted
- [x] Update Celery task (via `update_stale_prices`)
  - [x] Replace linear loop with batch processing

---

## Phase 3: Price History (Next)

### 3.1 Database Schema
- [ ] Update `models.py` to add `PriceHistory`
- [ ] Migration

### 3.2 History Recording
- [ ] Update `price_service.py` to save history on change

### 3.3 UI Implementation
- [ ] Add API endpoint for history data
- [ ] Add Sparkline to Item Card

---

## Phase 4: Refactoring (Pending)

- [ ] Split `price_service.py` into `services/price_extractors/` modules? (Evaluate if needed based on file size)
