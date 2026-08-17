---
status: OK
---

# ios-activity Arrow

The notification surface: Activity tab, APNs authorization + device registration,
and tapped-notification routing.

## Artifacts
- **LLD**: [docs/intent/boundary-ios/ios-activity.md](../../intent/boundary-ios/ios-activity.md)
- **EARS Specs**: [docs/intent/boundary-ios/ios-activity/ios-activity-specs.md](../../intent/boundary-ios/ios-activity/ios-activity-specs.md)
- **Tests**: `ios/WishlistKitTests/ActivityViewModelTests.swift`
- **Code**: `ios/Wishlist/Views/ActivityView.swift`, `ios/Wishlist/Views/RootTabView.swift`,
  `ios/Wishlist/Views/DeepLinkDetailView.swift`,
  `ios/Wishlist/PushManager.swift`, `ios/Wishlist/AppDelegate.swift`,
  `ios/Wishlist/WishlistApp.swift`,
  `ios/WishlistKit/PushPermissionPolicy.swift`, `ios/WishlistKit/Badge.swift`,
  `ios/WishlistKit/ViewModels/ActivityViewModel.swift`

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| Activity | IOS-ACT-001 to IOS-ACT-003 | 3 | 0 | 0 |
| Push     | IOS-ACT-004 to IOS-ACT-007 | 4 | 0 | 0 |
| Routing  | IOS-ACT-008, IOS-ACT-009 | 2 | 0 | 0 |
| Badge    | IOS-ACT-010 | 1 | 0 | 0 |

**Summary:** 10 of 10 active specs implemented.

## Key Findings

1. **`/items/<id>` links route to the item detail** — `RootTabView` parses the
   link, fetches item+owner via `APIClient.item(id:)`, and presents
   `DeepLinkDetailView` (own items → My List tab; bare links → Activity)
   (`RootTabView.swift:37-66`); a failed fetch shows an "Item not found" alert.
2. **Push authorization is requested once per install** — `PushPermissionPolicy`
   maps the OS status to request/register/skip before any prompt
   (`PushManager.swift:requestAuthorization`), unit-tested in WishlistKit
   (IOS-ACT-009).
3. **Badge mirrors unread count** — `Badge` caps at 99; `ActivityView` syncs via
   `.onChange(of: unreadCount)`; `PushManager` clears on notification tap
   (IOS-ACT-010).
4. **Registration failures are logged** (were silently swallowed).

## Work Required

### Nice to Have
1. Retry or surface device-registration failures beyond a log line.