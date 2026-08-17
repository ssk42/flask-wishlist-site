---
status: OK
---

# ios-auth Arrow

The client authentication seam: the `Session` state machine, the Keychain-backed
`TokenStore` shared with the Share Extension, the login screen, and dependency wiring.

## Artifacts
- **LLD**: [docs/intent/boundary-ios/ios-auth.md](../../intent/boundary-ios/ios-auth.md)
- **EARS Specs**: [docs/intent/boundary-ios/ios-auth/ios-auth-specs.md](../../intent/boundary-ios/ios-auth/ios-auth-specs.md)
- **Tests**: `ios/WishlistKitTests/SessionTests.swift`, `ios/WishlistKitTests/TokenStoreTests.swift`
- **Code**: `ios/WishlistKit/Session.swift`, `ios/WishlistKit/Auth/TokenStore.swift`,
  `ios/Wishlist/AppEnvironment.swift`, `ios/Wishlist/Views/LoginView.swift`

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| Core     | IOS-AUTH-001 to IOS-AUTH-006 | 6 | 0 | 0 |
| Session-restore | IOS-AUTH-007, IOS-AUTH-008 | 2 | 0 | 0 |

**Summary:** 8 of 8 active specs implemented.

## Key Findings

1. **`Session.bootstrap()` restores the session** from a stored token via
   `GET /api/v1/me`, clearing the token on 401 (`Session.swift:31-41`) — the
   "401 → loggedOut" promise is now realized at launch (IOS-AUTH-007).
2. **Logout affordance added** — gear-menu "Log out" on the My List tab with
   confirmation, calling `Session.logOut()` (`MyListView.swift`) (IOS-AUTH-008).
3. **In-memory cache fronts the Keychain** (`TokenStore.swift:72-79`) so the process
   stays authenticated even when unsigned builds can't write the shared group.

## Work Required

### Nice to Have
1. Reconsider delete-then-recreate token save for partial-failure persistence.