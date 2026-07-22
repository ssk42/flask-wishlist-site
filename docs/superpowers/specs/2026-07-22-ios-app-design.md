# iOS App Frontend — Design Spec

**Date:** 2026-07-22
**Status:** Approved (pending final spec review)
**Scope:** Native iOS app covering the core gift loop, plus the Flask JSON API (v1) that powers it.

## Goals

1. Native SwiftUI app with real iOS look & feel (not a web wrapper).
2. Push notifications for claims, comments, and event reminders.
3. Share Sheet extension: add a product to your wishlist directly from Safari/Amazon.

**V1 scope: the core gift loop.** Browse everyone's wishlists, add/edit/delete your own items (including via Share Sheet), claim/unclaim/purchase, notifications with push. Events, comments, split-gift contributions, price-history charts, and advanced filters remain website-only for v1.

**Prerequisites confirmed:** Apple Developer Program membership (active) — required for push and TestFlight distribution.

## Non-Goals (v1)

- Feature parity with the website (events, comments, split gifts, sparklines).
- Android or iPad-optimized layouts.
- Offline editing/sync (read-only cached data is acceptable; writes require connectivity).
- Replacing the PWA or website.

## Architecture Overview

Two workstreams:

1. **Backend:** new `blueprints/api_v1.py` mounted at `/api/v1` — JSON-only, token-authenticated, CSRF-exempt.
2. **iOS app:** SwiftUI (iOS 17+) in an `ios/` folder in this repo, with a Share Extension target and a shared `WishlistKit` framework.

Claim/unclaim/edit logic is extracted from `blueprints/items.py` into `services/item_service.py` so the web and API blueprints share one implementation (no behavior duplication or drift).

## Backend: API v1

### Auth endpoints

| Endpoint | Behavior |
|----------|----------|
| `POST /api/v1/auth/login` | Body `{email, family_code}` → `{token, user}`. Rate limited 5/min (same as web login). |
| `POST /api/v1/auth/logout` | Revokes the presented token and deletes the device registration if provided. |

### Users & items

| Endpoint | Behavior |
|----------|----------|
| `GET /api/v1/users` | Family members with item counts (Family tab). |
| `GET /api/v1/items?user_id=&status=&category=&q=` | Filtered item list, reusing existing filter logic. |
| `POST /api/v1/items` | Create item; same validation as web (`_validate_item_fields`, shared). |
| `PATCH /api/v1/items/<id>` | Edit item (owner or, for status-affecting ops, non-owner rules per existing logic). |
| `DELETE /api/v1/items/<id>` | Delete item (same permission rules as web). |
| `POST /api/v1/items/<id>/claim` | Claim (wraps shared service). |
| `POST /api/v1/items/<id>/unclaim` | Unclaim (wraps shared service). |
| `POST /api/v1/items/<id>/purchase` | Mark purchased (wraps shared service). |
| `GET /api/v1/my-claims` | Items current user has claimed/purchased for others. |
| `POST /api/v1/metadata` | Wraps existing metadata fetch for Share-Sheet prefill. |

### Notifications & devices

| Endpoint | Behavior |
|----------|----------|
| `GET /api/v1/notifications` | Current user's notifications, newest first. |
| `POST /api/v1/notifications/<id>/read` | Mark one read. |
| `POST /api/v1/notifications/read-all` | Mark all read. |
| `POST /api/v1/devices` | Register `{apns_token, platform}` for push. |
| `DELETE /api/v1/devices/<token>` | Unregister (called on logout). |

### Surprise protection (trust boundary)

**Enforced in the serializer, server-side.** When `item.user_id == current_user.id`, the JSON response omits `status` and `last_updated_by` entirely. The owner's view is indistinguishable from an unclaimed item at the API level — network inspection cannot spoil a gift. Client-side hiding is not an acceptable substitute.

### New models (Flask-Migrate migration)

- **ApiToken:** `id`, `user_id` (FK), `token_hash` (SHA-256 of the plaintext, unique, indexed), `created_at`, `last_used_at`, `revoked` (bool).
- **Device:** `id`, `user_id` (FK), `apns_token` (unique), `platform`, `created_at`.

### Token auth mechanics

- On login: `secrets.token_urlsafe(32)`; store SHA-256 hash only; return plaintext once.
- Requests: `Authorization: Bearer <token>`. A `@token_required` decorator resolves the token and sets the Flask-Login `current_user` context so shared services work unchanged.
- Tokens are long-lived (family-trust model) but revocable; `last_used_at` updated on use.

### Push notifications (APNs)

- Token-based APNs auth (`.p8` signing key) — works for dev and prod, no cert renewal.
- Implementation: lightweight HTTP/2 client (`aioapns` or `httpx` + `PyJWT`).
- Trigger: wherever a `Notification` row is created, enqueue a push to the recipient's devices via the existing Celery worker (web requests never block on APNs).
- APNs 410 (gone) responses delete the stale device token automatically.
- Payload includes the message and `item_id` (or notification target) for deep linking.
- Feature-flagged: the API functions fully before APNs is configured.
- Env vars: `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_KEY_P8`, `APNS_BUNDLE_ID`, `APNS_USE_SANDBOX`.

## iOS App

### Project shape

`ios/` folder in this repo. Xcode project with three targets:

1. **Wishlist** — main SwiftUI app, iOS 17+, no third-party dependencies.
2. **ShareExtension** — receives a URL, prefills via `POST /api/v1/metadata`, allows edits, posts the item.
3. **WishlistKit** — shared framework: `APIClient`, `Codable` models, Keychain access. Used by both other targets.

Auth token lives in a **shared Keychain access group** so app and extension authenticate identically after one login.

### Architecture

- Lightweight MVVM: one `@Observable` view-model per screen.
- `APIClient`: builds requests, attaches Bearer token, decodes `Codable` responses, maps 401 to a logged-out state.
- `Item` model has **optional `status`** — absent for the user's own items, so the type system mirrors the server's surprise protection.

### Screens

| Tab | Contents |
|-----|----------|
| Family | Member list → member's wishlist → item detail with claim/purchase actions |
| My List | Own items; add/edit/delete with web-equivalent fields (description, link, price, category, priority, size/color/quantity) |
| Claims | Claimed/purchased items with unclaim and mark-purchased |
| Activity | Notifications, unread badge, pull-to-refresh, tap-to-deep-link |

Plus a login screen (email + family code, once per device).

### Push & deep links

- `UNUserNotificationCenter` permission request on first login; APNs device token posted to `/api/v1/devices`.
- Notification taps deep-link to the relevant item/screen using payload data.

## Testing

### Backend (pytest, existing fixtures)

- Every `/api/v1` endpoint: happy path, auth failures (missing/bad/revoked token → 401), validation errors, rate limit on login.
- **Surprise protection:** own claimed item's JSON has no `status`/`last_updated_by` keys; the same item serialized for another user shows the real status.
- Service extraction regression: existing web test suite (317 tests) stays green.
- APNs tested with a mocked transport; no real pushes in CI.
- Coverage gate requires running the full suite (unit + browser).

### iOS

- XCTest for `APIClient` and view-models via stubbed `URLProtocol` (no network).
- Simulator-driven end-to-end verification against a local Flask server (login → browse → claim → notification flows).
- Deep-link handling tested with `.apns` payload files dropped on the simulator.

## Rollout

1. Ship API v1 to Heroku (invisible to website users; zero risk).
2. Build the app against simulator + local Flask; then point at Heroku.
3. Configure APNs (create `.p8` key + App ID in the developer account); test push on a physical iPhone via Xcode.
4. TestFlight internal group for the family.

## Risks & mitigations

- **Refactoring claim logic breaks the website** → extraction is behavior-preserving; existing test suite is the guard.
- **Token leak via DB backup/logs** → only hashes stored; revocation supported.
- **APNs misconfiguration blocks v1** → push is feature-flagged; app is fully usable without it.
- **Share Extension auth drift** → single `WishlistKit` + shared Keychain group; no duplicate auth paths.
