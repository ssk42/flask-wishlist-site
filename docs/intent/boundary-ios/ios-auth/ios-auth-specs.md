# ios-auth EARS Specifications

- `[x]` **IOS-AUTH-001**: The system shall start in the `loggedOut` state at launch
  and expose a `SessionState` of either `loggedOut` or `loggedIn(User)`.
- `[x]` **IOS-AUTH-002**: When the user submits valid email and family code, the
  system shall call the login endpoint, save the returned token to the token store,
  and transition to `loggedIn(User)`; on any error it shall return `false` with the
  state unchanged.
- `[x]` **IOS-AUTH-003**: When the user logs out, the system shall best-effort
  revoke the token server-side, clear the token store, and transition to `loggedOut`.
- `[x]` **IOS-AUTH-004**: The system shall offer a `TokenStoring` protocol backed by
  a `KeychainTokenStore` whose in-memory cache fronts the shared access group
  `com.reitz.wishlist.shared`, falling back to the app's default keychain group.
- `[x]` **IOS-AUTH-005**: The system shall keep the process authenticated even when
  no Keychain write succeeds (e.g. unsigned simulator builds) by caching the token
  in memory.
- `[x]` **IOS-AUTH-006**: The login screen shall allow submission only when both
  email and family code are non-empty, and shall show a failure state when login
  returns `false`.
- `[x]` **IOS-AUTH-007**: Where a stored token exists at launch, the system shall
  restore the `loggedIn` session from it via `GET /api/v1/me`, clearing the token
  and staying `loggedOut` on a 401 (no forced re-login for a live token).
- `[x]` **IOS-AUTH-008**: The app shall provide a logout affordance reachable
  from the UI (a gear-menu "Log out" on the My List tab) that confirms with the
  user and calls `Session.logOut()`.