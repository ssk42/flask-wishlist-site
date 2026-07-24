# API v1 Reference

`/api/v1` is a JSON-only, token-authenticated surface for native clients (the
iOS app). It reuses the same underlying services as the website (item
CRUD, claim/unclaim/purchase, notifications) so behavior never drifts
between the two. Implementation: `blueprints/api_v1.py`, `services/api_auth.py`,
`services/api_serializers.py`, `services/item_service.py`, `services/push_service.py`.

## Auth model

- **Bearer tokens, not sessions.** Every request except `POST /api/v1/auth/login`
  requires an `Authorization: Bearer <token>` header. A `before_request` hook
  on the blueprint rejects anything else with `401 unauthorized`.
- **Login:** `POST /api/v1/auth/login` with `{"email", "family_code"}`. The
  family code is compared with `hmac.compare_digest` against `FAMILY_PASSWORD`.
  On success, a new opaque token is minted (`secrets.token_urlsafe(32)`) and
  returned once, plaintext, in the response body: `{"token", "user"}`.
  Rate limited to 5 requests/minute (same as the web login).
- **Hashed at rest.** Only `hashlib.sha256(token).hexdigest()` is ever stored
  (`ApiToken.token_hash`, unique + indexed). The plaintext is never persisted,
  so a database leak can't be replayed as a credential. `last_used_at` is
  bumped on every successful resolution.
- **Resolution:** a Flask-Login `request_loader` (`app.py`) reads the
  `Authorization` header and calls `services.api_auth.resolve_token`, which
  looks up the hash and returns the associated `User` (only if
  `revoked=False`). This makes `current_user` work unchanged inside the
  blueprint, so it shares logic with the web app.
- **Logout:** `POST /api/v1/auth/logout` revokes the presented token
  (`ApiToken.revoked = True`). It does **not** delete any device registration
  — if the client wants to stop receiving push after logout it must call
  `DELETE /api/v1/devices/<token>` itself.
- **CSRF:** the entire blueprint is exempted (`csrf.exempt(api_v1_bp)` in
  `app.py`) — bearer-token auth replaces CSRF for this surface.

## Endpoints

All endpoints below require a valid Bearer token unless noted.

### Auth

| Method & path | Body | Success | Notes |
|---|---|---|---|
| `POST /api/v1/auth/login` | `{email, family_code}` | `200 {token, user}` | Public (no token needed). Rate limited 5/min. |
| `POST /api/v1/auth/logout` | — | `200 {ok: true}` | Revokes the presented token only. |

### Users & items

| Method & path | Body / query | Success | Notes |
|---|---|---|---|
| `GET /api/v1/users` | — | `200 {users: [...]}` | All family members, each with `item_count`. |
| `GET /api/v1/items` | `?user_id=&status=&category=&q=` | `200 {items: [...]}` | See surprise protection below for `status`. `q` matches `description` (substring, case-insensitive). |
| `POST /api/v1/items` | item fields (see below) | `201 {item}` | Owner is `current_user`; `status` starts `Available`. |
| `PATCH /api/v1/items/<id>` | partial item fields | `200 {item}` | Owner-only. Only keys present in the patch are persisted. |
| `DELETE /api/v1/items/<id>` | — | `200 {ok: true}` | Owner-only. |
| `POST /api/v1/items/<id>/claim` | — | `200 {item}` | See claim/unclaim/purchase rules below. |
| `POST /api/v1/items/<id>/unclaim` | — | `200 {item}` | |
| `POST /api/v1/items/<id>/purchase` | — | `200 {item}` | |
| `GET /api/v1/my-claims` | — | `200 {items: [...]}` | Items the current user has claimed/purchased for someone else. |
| `POST /api/v1/metadata` | `{url}` | `200 {...metadata}` | Wraps `price_service.fetch_metadata` for Share-Sheet prefill. |

Item fields accepted by create/update: `description` (required), `link`,
`image_url`, `category`, `priority` (one of `config.PRIORITY_CHOICES`,
defaults to the first choice), `event_id`, `price`, `size`, `color`,
`quantity` (integer 1–99). Validation reuses the same `FormValidator` /
`validate_item_fields` the web forms use.

Claim/unclaim/purchase rules (`services/item_service.py`, shared with the
web app):
- **claim:** fails if you own the item (`own_item`) or it isn't `Available`
  (`not_available`).
- **unclaim:** fails unless the item is `Claimed` by you (`not_claimer`).
- **purchase:** fails if you own the item (`own_item`), it's already
  `Purchased` (`already_purchased`), or it's `Claimed` by someone else
  (`claimed_by_other`). This is stricter than the legacy web edit form.

### Notifications & devices

| Method & path | Body | Success | Notes |
|---|---|---|---|
| `GET /api/v1/notifications` | — | `200 {notifications, unread_count}` | Newest first, capped at 100. |
| `POST /api/v1/notifications/<id>/read` | — | `200 {ok: true}` | 404 if not found or not yours. |
| `POST /api/v1/notifications/read-all` | — | `200 {ok: true}` | |
| `POST /api/v1/devices` | `{apns_token, platform?}` | `201 {ok: true}` | Registers/reassigns a device for push. `platform` defaults to `"ios"`. |
| `DELETE /api/v1/devices/<token>` | — | `200 {ok: true}` | Idempotent — succeeds even if the token isn't registered. Owner-scoped (only deletes your own device row). |

## Surprise protection

Enforced **server-side, in the serializer** (`services/api_serializers.py`),
not the client:

- `serialize_item(item, viewer)` includes `status` and `last_updated_by`
  **only when `item.user_id != viewer.id`**. When you view your own item,
  those two keys are omitted from the JSON entirely — not nulled, absent —
  so there's nothing for network inspection to reveal.
- `GET /api/v1/items?status=...` never lets a status filter surface the
  viewer's own items: the query adds `Item.user_id != current_user.id`
  whenever `status` is present, so filtering by `Claimed` can't be used to
  detect that your own item was claimed.

## Error envelope

Most error responses are `{"error": "<code>"}`, optionally with
`"message"` (a human-readable string) alongside it:

| Status | When | Shape |
|---|---|---|
| `400` | Validation failed on `POST /items` or `PATCH /items/<id>` | `{"errors": ["message", ...]}` — **plural, a list**, not the `{error}` envelope. |
| `400` | Missing required field elsewhere (`missing_apns_token`, `missing_url`) | `{"error": "<code>"}`, no message. |
| `401` | Missing/invalid/revoked token (`unauthorized`); bad login (`invalid_family_code`, `unknown_email`) | `{"error": "<code>"}`, no message. |
| `403` | `PATCH`/`DELETE /items/<id>` by a non-owner (`forbidden`) | `{"error": "forbidden"}`, no message. |
| `404` | Item or notification not found (or notification not yours) (`not_found`) | `{"error": "not_found"}`, no message. |
| `409` | Claim/unclaim/purchase rule violation (`own_item`, `not_available`, `not_claimer`, `already_purchased`, `claimed_by_other`) | `{"error": "<code>", "message": "<human text>"}` — the only path where `message` is populated. |
| `502` | `POST /metadata` upstream fetch raised an exception (`fetch_failed`) | `{"error": "fetch_failed"}`, no message. |

Clients should switch on the `error` code, not the HTTP status alone, and
must special-case `POST/PATCH /items` (400 with `errors: [...]`) separately
from every other error path.

## Push notifications (APNs)

Push is **feature-flagged**: `services/push_service.apns_enabled()` requires
all four of `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_KEY_P8`, `APNS_BUNDLE_ID` to
be set, or every send is a silent no-op. The API and web app work fully
without any Apple configuration.

Delivery: token-based APNs auth (`.p8` key, ES256-signed JWT), sent via
`httpx` (HTTP/2). Triggered from `services/notification_service.create_notification`
whenever a `Notification` row is created, dispatched through Celery
(`services/celery_tasks.send_push_task`) so web/API requests never block on
APNs. A `410` response from Apple means the device token is dead; the
`Device` row is deleted automatically.

### Environment variables

| Var | Meaning |
|---|---|
| `APNS_KEY_ID` | The Key ID of your APNs Auth Key (from the Apple Developer portal). |
| `APNS_TEAM_ID` | Your Apple Developer Team ID. |
| `APNS_KEY_P8` | The **contents** of the downloaded `.p8` key file (not a file path) — paste the whole PEM block, including `-----BEGIN PRIVATE KEY-----`/`-----END PRIVATE KEY-----`. |
| `APNS_BUNDLE_ID` | The iOS app's bundle identifier (used as `apns-topic`). |
| `APNS_USE_SANDBOX` | `"true"` to send to `api.sandbox.push.apple.com` (development builds/Xcode); unset or `"false"` for production `api.push.apple.com`. |

**Generating a `.p8` key:** in the Apple Developer portal, go to
**Certificates, Identifiers & Profiles → Keys → (+)**, enable the **Apple
Push Notifications service (APNs)** capability, and create the key. Apple
lets you download the `.p8` file **exactly once** — save it securely. The
Key ID is shown on the key's detail page; the Team ID is in the top-right
of the portal (or under **Membership**).

## Models

- **`ApiToken`** (`models.py`): `id`, `user_id` (FK), `token_hash` (SHA-256,
  unique, indexed), `created_at`, `last_used_at`, `revoked`.
- **`Device`** (`models.py`): `id`, `user_id` (FK), `apns_token` (unique),
  `platform` (default `"ios"`), `created_at`.
