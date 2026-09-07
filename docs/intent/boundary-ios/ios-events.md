# ios-events LLD

## Context and Design Philosophy

`ios-events` covers the client's surface for family occasions: the
Events tab that lists upcoming and past events, and the event detail that
shows the event's items. It is the client mirror of the server's
`GET /api/v1/events` / `GET /api/v1/events/<id>` contract (`docs/API_V1.md`
§ Events), plus the slice 2 write contract (`POST /api/v1/events`,
`PATCH` / `DELETE /api/v1/events/<id>`). Slice 1 was strictly read-only —
no create affordance, no RSVP, no mutations; slice 2 adds creator-side
create/edit/delete, gated by comparing `createdBy.id` to the session user id.

## Core Components

### `EventsView` + `EventsViewModel`
- **EventsView** (`ios/Wishlist/Views/EventsView.swift`): lists events in
  `Upcoming` (date ascending) and `Past` sections; empty state "No events yet".
  A failed load surfaces an inline error row with a Retry button that calls
  `vm.load()`. Rows navigate to `EventDetailView`, sharing the view model so
  edits/deletes land in the same lists. Takes the `Session` (like
  `MyListView`) to derive the client plus `currentUserID` for creator gating.
  A `+` toolbar button opens the `EventFormView` create sheet (IOS-EVT-006).
- **EventsViewModel** (`ios/WishlistKit/ViewModels/EventsViewModel.swift`):
  `load()` → `client.events()` then partitions into `upcoming` /
  `past` by device-calendar day, **full-replacing** both arrays.
  No optimistic updates. Writes use full-replace semantics on the server's
  authoritative copy: `create(name:date:)` inserts the 201 event into
  upcoming/past by day (IOS-EVT-006); `update(id:name:date:)` drops the stale
  row and re-inserts the 200 event, so a date edit may move partitions
  (IOS-EVT-007); `delete(_:)` removes the row on 200 `{ok:true}`, leaving
  linked items untouched (IOS-EVT-008). Write errors map to friendly strings:
  400 surfaces the first server message, 403/404 surface a friendly error and
  full-reload via `load()` (IOS-EVT-010).
- **EventDetailView** (`ios/Wishlist/Views/EventDetailView.swift`): header
  (name, full date, creator) plus the event's items rendered as `ItemRow`s;
  item rows reuse the masked `serialize_item(viewer)` view so an owner's own
  items never leak claim status. Creator-only toolbar menu (Edit/Delete)
  renders only when `createdBy.id == currentUserID`; edit opens the prefilled
  `EventFormView` sheet and refreshes the header from the view model,
  delete confirms ("Items are kept, unlinked from this event.") then pops on
  success (IOS-EVT-007/008/009).
- **EventFormView** (`ios/Wishlist/Views/EventFormView.swift`): name field
  (required — Save disabled when blank/saving) plus a day `DatePicker`;
  `onSave` returning `false` keeps the form open with an inline message so
  edits are not lost (IOS-EVT-006/007/010).

### `WishlistEvent` + `APIClient` reads/writes (WishlistKit)
- **WishlistEvent** (`ios/WishlistKit/Models/WishlistEvent.swift`): `id`,
  `name`, `date: Date` decoded from the `"YYYY-MM-DD"` string, `createdBy`
  lite struct (`{id, name}`), `itemCount`, and detail-only `items`.
  `isUpcoming` compares `Calendar.current.startOfDay(for: date)` against
  today's start-of-day — never a raw `Date()` comparison (IOS-EVT-005).
  `dayString` encodes back to `"YYYY-MM-DD"` for write payloads (IOS-EVT-006).
- **APIClient.events()** → `GET /api/v1/events` (`{events: [...]}`);
  **APIClient.event(id:)** → `GET /api/v1/events/<id>`
  (`{event, items:[serialize_item(viewer)]}`), following the existing
  `send`/envelope conventions. Detail items with absent `status` read as
  `isOwn` via the shared `Item` type.
- **APIClient.createEvent(name:date:)** → `POST /api/v1/events`
  `{name, date "YYYY-MM-DD"}` → 201 `{event}` (IOS-EVT-006);
  **APIClient.updateEvent(id:name:date:)** → `PATCH /api/v1/events/<id>`
  (partial — nil fields omitted) → 200 `{event}` (IOS-EVT-007);
  **APIClient.deleteEvent(id:)** → `DELETE /api/v1/events/<id>` → 200
  `{ok:true}` (IOS-EVT-008). 400 decodes `{"errors":[...]}` via the shared
  `APIError.validation` path (IOS-EVT-010).

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| `[inferred]` Creator gating via `createdBy` compare | Edit/delete render only when `createdBy.id == session user id` (nil while logged out) | Server-driven `can_edit` flag | The id is already in the list payload; no new field, no extra fetch (IOS-EVT-009). |
| `[inferred]` Full-reload-after-write on 403/404, last-write-wins | `load()` then friendly error; concurrent edits just overwrite | Conflict (409) UI / merge | Server has no versioning; reload restores the authoritative list, no conflict UI to maintain (IOS-EVT-010). |
| `[inferred]` Delete keeps items, confirms first | Confirm copy "items are kept, unlinked"; remove row on `{ok:true}` | Silent delete / cascade UI | Server nulls `event_id` instead of deleting items; the copy says so upfront (IOS-EVT-008). |
| `[inferred]` No optimistic updates | Full replace on `load()` | Append/merge | List is authoritative; simpler correct state, mirrors `ActivityViewModel`. |
| `[inferred]` Date transport stays a `"YYYY-MM-DD"` string | Decode to `Date` at the model layer | Epoch/datetime | Matches server contract; day-granular display needs no time component. |
| `[inferred]` Slice 1 hides creation | No create affordance | Disabled create button | Read-only slice; a visible-but-dead button invites confusion (IOS-EVT-003). |

## Open Questions & Future Decisions

### Resolved
1. ✅ Event list is family-visible with no user filter — the server exposes
   all events; the client partitions locally (IOS-EVT-001).
2. ✅ Today belongs to upcoming — the boundary is the device-calendar day via
   `Calendar.current.startOfDay`, not a 24h window (IOS-EVT-005).
3. ✅ Failure copy is "Couldn't load events." with a retry action that
   re-invokes `load()` (IOS-EVT-004).
4. ✅ Creator-side create inserts the 201 event into upcoming/past by
   device-calendar day; validation failures surface the server message
   (IOS-EVT-006).
5. ✅ Creator-side edit replaces the row from the 200 event (date edits may
   move partitions); delete confirms, then removes the row, items kept
   (IOS-EVT-007/008).
6. ✅ Edit/delete controls render only for the creator (`createdBy.id ==
   session user id`); 403/404 surfaces a friendly error and reloads, with
   last-write-wins and no conflict UI (IOS-EVT-009/010).

### Deferred
1. RSVP/attendance tracking (slice 3).
2. Device-calendar sync (e.g. adding an event to the system calendar).

## References

- `docs/intent/boundary-ios/ios-events/ios-events-specs.md`
- Server mirror: `docs/API_V1.md` § Events
- Tests: `ios/WishlistKitTests/APIClientEventsTests.swift`, `ios/WishlistKitTests/EventsViewModelTests.swift`
- Code: `ios/Wishlist/Views/EventsView.swift`,
  `ios/Wishlist/Views/EventDetailView.swift`,
  `ios/Wishlist/Views/EventFormView.swift`,
  `ios/WishlistKit/Models/WishlistEvent.swift`,
  `ios/WishlistKit/Networking/APIClient.swift`,
  `ios/WishlistKit/ViewModels/EventsViewModel.swift`
