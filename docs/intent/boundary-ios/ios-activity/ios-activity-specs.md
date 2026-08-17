# ios-activity EARS Specifications

- `[x]` **IOS-ACT-001**: The system shall load and display notifications on the
  Activity tab, showing an unread count and distinguishing unread entries.
- `[x]` **IOS-ACT-002**: When the user taps a notification, the system shall mark it
  read via `POST /api/v1/notifications/{id}/read` and reload the list.
- `[x]` **IOS-ACT-003**: When unread notifications exist, the system shall offer a
  "Read all" action that posts `/api/v1/notifications/read-all` and reloads.
- `[x]` **IOS-ACT-004**: When the user first reaches a logged-in state, the system
  shall request notification authorization; if granted, it shall register for remote
  notifications.
- `[x]` **IOS-ACT-005**: When a device token is received, the system shall hex-encode
  it and best-effort POST `{apns_token, platform:"ios"}` to `/api/v1/devices`.
- `[x]` **IOS-ACT-006**: When the user taps a push notification, the system shall
  route to the Activity tab.
- `[x]` **IOS-ACT-007**: While the app is foregrounded, an incoming notification
  shall present as a banner/sound/badge via the notification center delegate.
- `[x]` **IOS-ACT-008**: Where a push notification carries a `link` payload of
  `/items/<id>`, the system shall fetch the item and its owner and present the item
  detail (own items via the My List tab, others' items via the Family tab); a bare
  link shall switch to the Activity tab.
- `[x]` **IOS-ACT-009**: The system shall request notification authorization at
  most once per install — the OS authorization status is consulted first
  (`.notDetermined` → request; `.authorized`/`.provisional`/`.ephemeral` →
  register without prompting; `.denied` → skip).
- `[x]` **IOS-ACT-010**: The system shall mirror the unread notification count on
  the app-icon badge (capped at 99), syncing when the Activity tab loads and
  clearing it when the user taps a notification or marks all read.