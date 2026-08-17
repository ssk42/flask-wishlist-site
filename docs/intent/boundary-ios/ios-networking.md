# ios-networking LLD

## Context and Design Philosophy

`ios-networking` is the shared networking and model layer inside the `WishlistKit`
framework, consumed by the main `Wishlist` app and the `ShareExtension` (both link
the framework). It owns every request against the Flask `/api/v1` JSON surface and
the Codable types that mirror its responses. The guiding principle is that the
client never reimplements server rules: claim/ownership conflicts are surfaced as
server conflict codes and mapped to user copy; surprise protection is preserved by
the model types themselves (`status`/`lastUpdatedBy` absent for the viewer's own
items), never synthesized back.

## Core Components

### `APIClient` (actor) — `ios/WishlistKit/Networking/APIClient.swift`
Actor with `baseURL`, an injected `URLSession` (default `.shared`), a `tokenProvider`
closure (`() async -> String?`), and a shared `JSONDecoder`. `send<T:Decodable>`
decodes or throws `APIError.decoding`; `sendRaw` builds URLs with
`URL(string: path, relativeTo: baseURL)` — deliberately NOT `appendingPathComponent`,
which percent-encodes the leading slash (APIClient.swift:124-131). Bodies are
`JSONSerialization`-serialized with `compactMapValues { $0 }` dropping nils
(:133-137). Bearer header added only when `authenticated && tokenProvider() != nil`
(:139-141).

**Endpoint surface** (all Bearer-authenticated except `login`):

| Method | Path | Body | Success |
|---|---|---|---|
| POST | `/api/v1/auth/login` | `{email, family_code}` | `{token, user}` |
| POST | `/api/v1/auth/logout` | — | `200 {ok}` |
| GET | `/api/v1/users` | — | `{users:[User]}` |
| GET | `/api/v1/items` | `user_id,status,category,q` filters | `{items:[Item]}` |
| GET | `/api/v1/my-claims` | — | `{items:[Item]}` |
| GET | `/api/v1/notifications` | — | `{notifications, unread_count}` |
| POST | `/api/v1/items` | `ItemDraft.payload` | `201 {item}` |
| PATCH | `/api/v1/items/{id}` | `ItemDraft.payload` | `{item}` |
| DELETE | `/api/v1/items/{id}` | — | `{ok}` |
| POST | `/api/v1/items/{id}/claim` | — | `{item}` |
| POST | `/api/v1/items/{id}/unclaim` | — | `{item}` |
| POST | `/api/v1/items/{id}/purchase` | — | `{item}` |
| POST | `/api/v1/notifications/{id}/read` | — | `{ok}` |
| POST | `/api/v1/notifications/read-all` | — | `{ok}` |
| POST | `/api/v1/devices` | `{apns_token, platform:"ios"}` | `201 {ok}` |
| DELETE | `/api/v1/devices/{apnsToken}` | — | `{ok}` |
| POST | `/api/v1/metadata` | `{url}` | metadata dict |
| GET | `/api/v1/me` | — | `{user}` (current user for session restore) |
| GET | `/api/v1/items/{id}` | — | `{item, owner}` (single-item fetch + owner for deep links) |

**Error mapping**: `200…299` OK; `401` → `unauthorized`; `409` → `conflict(code:)`
reading top-level `error`; `400` → `validation([String])` reading top-level
`errors`; else `http(status, code)`. Transport errors → `transport(String)`.

**Session restore flow** (`IOS-AUTH-007`): `Session.bootstrap()` reads a stored token
via the injected `TokenStoring`; if present it calls `GET /api/v1/me` and, on 200,
transitions to `.loggedIn(user)`. A `401` clears the token and keeps `.loggedOut`.
This is what delivers the doc comment's original "first API call that returns 401
bounces back to loggedOut" promise at launch.

**Deep-link item fetch** (`IOS-ACT-008`): `GET /api/v1/items/{id}` returns
`{item, owner}`, where `owner` is the item's `User` via `serialize_user`. Surprise
protection is preserved server-side (`serialize_item` omits `status`/`last_updated_by`
when the item is the viewer's own). The client uses the `owner` to build a
`MemberItemsViewModel` for routing a tapped push notification to the item detail.

### Codable models — `ios/WishlistKit/Models/`
- **Item** (`Item.swift`): snake_case CodingKeys; **`status` and `lastUpdatedBy`
  are Optional** — the server omits both for the viewer's own items; `isOwn`
  derives as `status == nil` (:40). **Never default a missing status.**
- **User** (`User.swift`): `id`, `name`, `email`, optional `itemCount` (`item_count`).
- **WishlistNotification** (`WishlistNotification.swift`): `id`, `message`,
  non-optional `link`, `isRead` (`is_read`), `createdAt` (`created_at`).

### `ItemDraft` — `ios/WishlistKit/Networking/ItemDraft.swift`
Write-model for create/update: 9 optional fields (description, link, price,
category, priority, size, color, quantity). `payload` omits nil so PATCH is a true
partial update. No `status` field — state changes happen only through the
claim/unclaim/purchase endpoints.

### `WishlistAPI` — `ios/WishlistKit/WishlistAPI.swift`
Backend-location singleton. `defaultBaseURL` defaults to production
`https://gifts.stevereitz.dev` (:7), local `http://localhost:8000` (:12), and is
overridable via a `WLAPIBaseURL` string in the target `Info.plist` (:18-24). Also
exposes `sharedKeychainGroup` = `com.reitz.wishlist.shared` (:28).

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| `[inferred]` Actor `APIClient` with injected `URLSession` for tests | Actor + `URLProtocol` stub | Mock classes; direct URLSession | Tests run offline via a stubbed `URLProtocol`; actor isolates state. |
| `[inferred]` Bearer token from injected `tokenProvider` | Provider closure | Reading Keychain inside client | Decouples networking from auth; extension and app share one API client with different providers. |
| `[inferred]` `URL(string:relativeTo:)` for path building | Relative-string URLs | `appendingPathComponent` | The latter percent-encodes the leading slash (comment :124-127). |
| `[inferred]` Surprise protection mirrored in types (`status`/`lastUpdatedBy` Optional) | Optional status | Defaulting to `"Available"` | A nil status means "my own item, status hidden"; defaults would leak claim state. |
| `[inferred]` `ItemDraft` omits nil in `payload` | Partial-update dict | Sending all fields | PATCH must only persist the keys present; also nil-filtered again by `sendRaw`. |
| `[inferred]` Base URL via `WLAPIBaseURL` plist override | Plist key | Build-config per scheme | Points any build (test/dev/prod) without editing code. |

## Open Questions & Future Decisions

### Resolved
1. ✅ Base URL default is the deployed host, not localhost — `AppEnvironment.swift`'s
   comment ("defaults to the local Flask server") is stale relative to
   `WishlistAPI.defaultBaseURL` (`AppEnvironment.swift:1-20`).
2. ✅ `fetchMetadata` now decodes a typed `MetadataEnvelope` via the shared decoder
   — no JSONSerialization double-parse.
3. ✅ Nil-filtering consolidated: `ItemDraft.payload` returns the raw `[String:Any?]`
   dict and `sendRaw`'s `compactMapValues` is the single drop point.

### Deferred
1. `unregisterDevice` embeds the raw APNs token in the DELETE URL path — confirm
   the server hashes/truncates it before logging paths.
2. `Placeholder.swift` is vestigial (pre-real-code marker enum) — candidate for
   deletion.

## References

- `docs/API_V1.md` — the exact server contract this client mirrors.
- `docs/intent/boundary-ios/ios-networking/ios-networking-specs.md`
- Tests: `ios/WishlistKitTests/APIClientTests.swift`,
  `ios/WishlistKitTests/APIClientReadTests.swift`,
  `ios/WishlistKitTests/APIClientWriteTests.swift`,
  `ios/WishlistKitTests/ModelDecodingTests.swift`,
  `ios/WishlistKitTests/WishlistAPITests.swift`,
  `ios/WishlistKitTests/Support/StubURLProtocol.swift`