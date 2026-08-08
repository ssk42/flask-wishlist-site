# Price Stealth System Design (LLD)

## Overview
The Price Stealth system provides an automated, evasion-resistant mechanism for extracting product prices from Amazon. It employs browser identity rotation, persistent session cookies via Redis, Playwright stealth plugins, and human-like interaction behaviors to avoid CAPTCHAs and blocking.

## Architecture
- **Extractor (`services/amazon_stealth/extractor.py`)**: Uses Playwright and `playwright_stealth` to emulate real browsers. Uses `AmazonPriceExtractor` for HTML parsing. Handles CAPTCHA detection and rate limit classification.
- **Identity Manager (`services/amazon_stealth/identity_manager.py`)**: Rotates among 12 predefined browser fingerprints (Mac, Windows, Linux x Chrome, Safari, Edge, Firefox). Persists request counts and burned statuses in Redis.
- **Behaviors (`services/amazon_stealth/behaviors.py`)**: Simulates human interactions (bezier curve mouse movements, variable scrolling, random delays) and automatically clicks cookie consent banners.
- **Identities (`services/amazon_stealth/identities.py`)**: Defines browser identity profiles containing User-Agent, Viewport, WebGL vendor, WebGL renderer, locale, timezone, device scale, and color scheme.

## Key Design Decisions
- **[inferred] Redis for State Persistence**: Redis is used for tracking request counts, "burned" status, and caching cookies per identity, ensuring state is shared across multiple asynchronous workers or instances.
- **[inferred] Quadratic Bezier Mouse Movements**: Implementing bezier curves with noise to generate human-like mouse trails to defeat anti-bot heuristics.
- **[inferred] Adaptive Rotation Thresholds**: Rotating identities every 10-20 requests (randomly chosen) to prevent predictable usage patterns that could trigger rate limits.
- **[inferred] 24-hour Burn Timeout**: If an identity hits a CAPTCHA or gets blocked, it is "burned" (excluded from use) for 24 hours.

## Open Questions
- **TODO/Quirk**: `generate_bezier_points` tracks previous position using `window._mouseX`, but the starting point fallback `(640, 400)` might jump instantly if the actual mouse is elsewhere or if it's the first move.
- **TODO/Quirk**: No proxy rotation is implemented. The IPs remain the same even as the browser fingerprint rotates, which could lead to IP-level blocking.
- **TODO/Quirk**: `stealth_fetch_amazon` falls back to `AmazonFailureType.NETWORK_ERROR` if `playwright_stealth` is not installed, rather than attempting without stealth or raising a more descriptive configuration error.
