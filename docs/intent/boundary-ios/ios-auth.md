# ios-auth LLD

## Context and Design Philosophy

`ios-auth` owns authentication state in the client: the `Session` state machine
that drives the root UI switch, the `KeychainTokenStore` that persists the bearer
token, and the `LoginView` where a user authenticates. The design intent is a thin,
testable seam between "what the user is doing" (logged out vs in) and the token
storage that makes API calls possible. The token store is deliberately shared with
the Share Extension through a shared Keychain access group.

## Core Components

### `Session` — `ios/WishlistKit/Session.swift`
`@MainActor @Observable`; `state` is `private(set)`, typed as
`SessionState.loggedOut | .loggedIn(User)` (:4-6), starting `.loggedOut` (:11).
Injected `APIClient` + `TokenStoring` (:10-18).

- **`logIn(email:familyCode:)`** (:27-35): `client.login` → `tokenStore.save(token)`
  → `state = .loggedIn(user)`; returns `true`. Any thrown error → returns `false`,
  `state` unchanged.
- **`logOut()`** (:38-41): best-effort `try? client.logout()` → `tokenStore.clear()`
  → `state = .loggedOut`.
- **`bootstrap()`** (:24): reads a stored token via `TokenStoring` and, when one is
  present, calls `GET /api/v1/me` to restore the `User`. On `200` it transitions to
  `.loggedIn(user)`; on `401` it clears the token and stays `.loggedOut`. It is
  invoked at launch and delivers the "first API call that returns 401 → loggedOut"
  behavior documented on the session. With no stored token it is a no-op.

### `TokenStore` — `ios/WishlistKit/Auth/TokenStore.swift`
- Protocol `TokenStoring` (`read`/`save`/`clear`, :4-7) with two conformers:
  - `InMemoryTokenStore`: NSLock-guarded optional string, pure ephemeral (:10-16).
  - `KeychainTokenStore` (:26-88): service `com.reitz.wishlist`, account
    `api-token`, default access group `com.reitz.wishlist.shared`.
    - **Read** (:56-68): memory `cached` first; miss → `SecItemCopyMatching` across
      `groupsToTry`, repopulating cache.
    - **Save** (:72-79): sets `cached` FIRST (keeps the process authenticated even
      when every Keychain write fails — e.g. unsigned simulator builds), then
      clears+re-adds across groups, `kSecAttrAccessibleAfterFirstUnlock`, until one
      succeeds.
    - **Group fallback** (:36-43): shared access-group `com.reitz.wishlist.shared`
      first (signed device/TestFlight, readable by the Share Extension), then the
      app's default keychain group (the only thing that works on unsigned
      simulator builds lacking the entitlement).

### `AppEnvironment` — `ios/Wishlist/AppEnvironment.swift`
Dependency wiring: `tokenStore` (KeychainTokenStore on shared group),
`client` (APIClient with `tokenProvider: { tokenStore.read() }`), and a
`@MainActor makeSession()`. Both `tokenStore` and `client` are non-isolated
`Sendable` so the client's `@Sendable` token provider reads from any context.

### `LoginView` — `ios/Wishlist/Views/LoginView.swift`
Email + family-code `SecureField` (no password). Submit disabled until both
non-empty (:83-85). `submit()` (:99-104) → `session.logIn`, failed flag on `false`.

### Logout affordance — `ios/Wishlist/Views/MyListView.swift`
The My List tab's navigation bar carries a gear `Menu` (topBarTrailing) with a
destructive "Log out" item; tapping it shows a `confirmationDialog` ("Your saved
items stay on your wishlist.") whose confirm action calls `await session.logOut()`.
Chosen location: My List is the user's own-list surface, always reachable
regardless of list state, and `Session.logOut()` was previously unreachable from
the UI (IOS-AUTH-008).

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| `[inferred]` In-memory cache fronts the Keychain | Cache + Keychain fallback | Keychain only | Unsigned simulator builds can't write the shared access group; the cache keeps the process authenticated for the session (README documents re-login on relaunch). |
| `[inferred]` Shared access group `com.reitz.wishlist.shared` | Shared Keychain group | Separate per-process tokens | Lets the Share Extension authenticate without its own login UI. |
| `[inferred]` Family code (not password) | Email + `family_code` | Individual passwords | Mirrors the server auth model. |
| `[inferred]` `Session.logOut` clears token then transitions | Eager local clear | Server-first | Bounded logout even when the network fails (best-effort server call). |

## Open Questions & Future Decisions

### Resolved
1. ✅ Logout affordance added — gear-menu "Log out" on the My List tab with
   confirmation, calling `Session.logOut()` (IOS-AUTH-008).
2. ✅ `Session.bootstrap()` is no longer a no-op — it restores the session from a
   stored token via `GET /api/v1/me` (IOS-AUTH-007).

### Deferred
1. Delete-then-recreate on token save: a partially failing Keychain could lose
   persistence for the app's own process (in-memory cache papers over it).

## References

- `docs/intent/boundary-ios/ios-auth/ios-auth-specs.md`
- Tests: `ios/WishlistKitTests/SessionTests.swift`,
  `ios/WishlistKitTests/TokenStoreTests.swift`
- Code: `ios/WishlistKit/Session.swift`, `ios/WishlistKit/Auth/TokenStore.swift`,
  `ios/Wishlist/AppEnvironment.swift`, `ios/Wishlist/Views/LoginView.swift`