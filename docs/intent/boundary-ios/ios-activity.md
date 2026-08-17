# ios-activity LLD

## Context and Design Philosophy

`ios-activity` covers the client's notification surface: the Activity tab that lists
newly claimed/purchased/commented items, and the push-notification plumbing that
(1) requests authorization, (2) registers the APNs device token with the server, and
(3) routes a tapped notification back into the app. It is the client mirror of the
server's `system-tasks`/notification push flow.

## Core Components

### `ActivityView` + `ActivityViewModel`
- **ActivityView** (`ios/Wishlist/Views/ActivityView.swift`): lists notifications;
  unread = wlAccent dot + semibold; tap → `vm.markRead` only; "Read all" title
  accessory when `unreadCount > 0` (:8-12). Empty state "All caught up". Does NOT
  navigate from `notification.link`.
- **ActivityViewModel** (`ios/WishlistKit/ViewModels/ActivityViewModel.swift`):
  `load()` → `client.notifications()` sets `notifications` + `unreadCount`
  (:14-24); `markRead(_)` guards `!isRead`, calls endpoint, then **full reload**
  (:27-34); `markAllRead()` → endpoint + reload (:37-42). No optimistic updates.

### Push plumbing (app target)
- **WishlistApp** (`WishlistApp.swift:9-16`): `.onChange(of: session.state)` — on
  every transition to `.loggedIn`, calls `PushManager.requestAuthorization()`.
- **PushManager** (`ios/Wishlist/PushManager.swift`): `@MainActor` singleton,
  `UNUserNotificationCenterDelegate`.
  - `start()` (:25-27): sets the notification center delegate.
  - `requestAuthorization()` (:31-52): consults
    `PushPermissionPolicy.action(for: settings.authorizationStatus)` first —
    `.notDetermined` requests permission then registers if granted;
    `.authorized`/`.provisional`/`.ephemeral` registers without prompting;
    `.denied` skips. The OS status is the once-per-install source of truth
    (IOS-ACT-009).
  - `PushPermissionPolicy` (`ios/WishlistKit/PushPermissionPolicy.swift`): pure
    status→action mapping, unit-tested in WishlistKit.
  - `Badge` (`ios/WishlistKit/Badge.swift`): app-icon badge policy (unread count,
    capped at 99), unit-tested in WishlistKit (IOS-ACT-010). `ActivityView` syncs
    it via `.onChange(of: vm.unreadCount)`; `PushManager` clears it on notification
    tap.
  - `deviceTokenReceived(_:)` (:33-37): hex-encodes the token,
    `POST /api/v1/devices` with `{apns_token, platform:"ios"}`; failures are logged
    (were silently swallowed).
  - `userNotificationCenter` `willPresent` → `[.banner, .sound, .badge]` (:41-45).
  - `didReceive` (:48-54): reads `link` from `userInfo`, posts
    `openLinkNotification` on NotificationCenter with `["link": link ?? ""]`.
- **AppDelegate** (`AppDelegate.swift`): `didFinishLaunching` → `PushManager.start()`
  (:7-10); `didRegisterForRemoteNotificationsWithDeviceToken` → `deviceTokenReceived`
  (:12-15); `didFailToRegister` prints "expected on simulator" (:17-21).
- **RootTabView** deep-link (:27-30): `.onReceive(openLinkNotification)` reads the
  `link` payload. For a `/items/<id>` link it fetches the item + owner via
  `APIClient.item(id:)` and presents the `ItemDetailView` (fed by a
  `MemberItemsViewModel` for that owner) as a full-screen cover on the owning tab —
  own items route to the My List tab, others' items to the Family tab. A bare link
  (no item path) falls back to switching to the Activity tab (the previous behavior).

### Entitlements / Info.plist
`Wishlist.entitlements`: `aps-environment = development`; `Info.plist`:
`UIBackgroundModes = [remote-notification]`.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| `[inferred]` Token registered only after a grant | Ask permission → register | Register always | Avoids pointless token registration when the user declines. |
| `[inferred]` Device token hex-encoded | hex string in `apns_token` | Raw data | Matches server `Device.apns_token` string column. |
| `[inferred]` Tap → NotificationCenter bus → tab switch | NotificationCenter | Direct navigation | Decouples PushManager from view hierarchy; RootTabView subscribes. |
| `[inferred]` No optimistic reads | Full reload after markRead/all | Local flip | Keeps unread count authoritative; simpler correct state. |

## Open Questions & Future Decisions

### Resolved
1. ✅ Notification taps reliably select Activity. Item-shaped `link` payloads
   (e.g. `/items/42`) are now routed to the item detail cover (IOS-ACT-008); bare
   links still switch to Activity.
2. ✅ Push authorization is now requested at most once per install — the OS status
   is consulted before prompting (IOS-ACT-009).
3. ✅ App-icon badge mirrors the unread count (capped at 99), synced from
   `ActivityView.unreadCount` and cleared on notification tap (IOS-ACT-010).
4. ✅ Device-registration failures are logged (were silently swallowed).

### Deferred
1. Registration errors are logged but not retried or shown to the user — a future
   session could add retry-on-foreground or a settings surface.

## References

- `docs/intent/boundary-ios/ios-activity/ios-activity-specs.md`
- Server mirror: `docs/API_V1.md` § Notifications & devices
- Tests: `ios/WishlistKitTests/ActivityViewModelTests.swift`
- Code: `ios/Wishlist/Views/ActivityView.swift`, `ios/Wishlist/Views/RootTabView.swift`,
  `ios/Wishlist/PushManager.swift`, `ios/Wishlist/AppDelegate.swift`,
  `ios/Wishlist/WishlistApp.swift`,
  `ios/WishlistKit/ViewModels/ActivityViewModel.swift`