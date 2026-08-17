---
status: OK
---

# ios-share Arrow

The Safari Share-extension target: extract a shared URL, prefill and edit an item,
post it to the user's own wishlist using the token the app stored in the shared
Keychain group.

## Artifacts
- **LLD**: [docs/intent/boundary-ios/ios-share.md](../../intent/boundary-ios/ios-share.md)
- **EARS Specs**: [docs/intent/boundary-ios/ios-share/ios-share-specs.md](../../intent/boundary-ios/ios-share/ios-share-specs.md)
- **Tests**: `ios/WishlistKitTests/ShareItemViewModelTests.swift`
- **Code**: `ios/ShareExtension/ShareViewController.swift`, `ios/ShareExtension/ShareView.swift`,
  `ios/ShareExtension/ShareExtension.entitlements`, `ios/ShareExtension/Info.plist`,
  `ios/WishlistKit/ViewModels/ShareItemViewModel.swift`

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| Core     | IOS-SHARE-001 to IOS-SHARE-005 | 5 | 0 | 0 |

**Summary:** 5 of 5 active specs implemented.

## Key Findings

1. **No login UI in the extension** — it authenticates with the app's token from
   the shared Keychain access group; on missing/401 token it surfaces "open the app
   and log in" (IOS-SHARE-004). Only verifiable on a signed device build.
2. **Prefill is best-effort** — always keeps the shared URL as `link`, then fetches
   metadata silently; submission never blocks on lookup (IOS-SHARE-002).
3. **URL extracted from `public.url` or plain-text HTTP token** (`ShareViewController.swift:69-90`).
4. **Design tokens duplicated** — `ShareView.swift` carries its own `wlShareBg`
   because `Theme.swift` lives in the app target, not the extension's linked
   `WishlistKit`.

## Work Required

### Nice to Have
1. Extract shared design tokens into `WishlistKit` so the extension matches the full
   palette instead of duplicating one color.