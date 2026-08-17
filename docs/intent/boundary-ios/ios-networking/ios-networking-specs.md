# ios-networking EARS Specifications

- `[x]` **IOS-NET-001**: The system shall authenticate every `/api/v1` request except
  `POST /api/v1/auth/login` with an `Authorization: Bearer <token>` header read from
  the injected `tokenProvider`.
- `[x]` **IOS-NET-002**: When the user logs in, the system shall POST
  `{email, family_code}` to `/api/v1/auth/login` and decode the returned `{token, user}`.
- `[x]` **IOS-NET-003**: When fetching items, the system shall include only the
  non-nil of the `user_id`, `status`, `category`, and `q` query parameters.
- `[x]` **IOS-NET-004**: The `Item` model shall make `status` and `lastUpdatedBy`
  optional, deriving `isOwn` from `status == nil`, so the viewer's own (surprise-
  protected) items expose no claim state.
- `[x]` **IOS-NET-005**: When a request fails, the system shall map status codes to
  `APIError`: `401` → `unauthorized`, `409` → `conflict(code:)` (from top-level
  `error`), `400` → `validation([String])` (from top-level `errors`), and any other
  non-2xx → `http(status, code)`; transport failures → `transport(String)`.
- `[x]` **IOS-NET-006**: When building an item draft for `PATCH`, the system shall
  omit nil fields so the request is a true partial update; item drafts shall carry
  no `status` field.
- `[x]` **IOS-NET-007**: When `ItemDraft` or a request body is serialized, the system
  shall drop nil values via `compactMapValues`.
- `[x]` **IOS-NET-008**: The system shall resolve the API base URL from
  `WishlistAPI.defaultBaseURL` (production `https://gifts.stevereitz.dev`), overridable
  by a `WLAPIBaseURL` string in the target `Info.plist`.
- `[x]` **IOS-NET-009**: When fetching metadata for a shared URL, the system shall
  decode `title` → `description`, plus `price` and `image_url`, via a typed
  envelope; a decode/transport failure throws `APIError` (callers fall back to a
  link-only draft).
- `[x]` **IOS-NET-010**: When registering a device for push, the system shall POST
  `{apns_token, platform: "ios"}` to `/api/v1/devices`; unregistration shall DELETE
  `/api/v1/devices/{apnsToken}`.
- `[x]` **IOS-NET-011**: When marking notifications read, the system shall POST to
  `/api/v1/notifications/{id}/read` each individually and `/api/v1/notifications/read-all`
  for all.
- `[x]` **IOS-NET-012**: The system shall fetch the current user's profile via
  `GET /api/v1/me` to restore a session from a stored bearer token.
- `[x]` **IOS-NET-013**: The system shall fetch a single item via
  `GET /api/v1/items/{id}` and decode both the item and its owner, so a deep link
  can build the owner-scoped detail view without preloading a member's whole list.