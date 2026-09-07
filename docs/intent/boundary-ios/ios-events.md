# ios-events LLD

## Context and Design Philosophy

`ios-events` covers the client's read-only surface for family occasions: the
Events tab that lists upcoming and past events, and the event detail that
shows the event's items. It is the client mirror of the server's
`GET /api/v1/events` / `GET /api/v1/events/<id>` contract (`docs/API_V1.md`
§ Events). Slice 1 is strictly read-only — no create affordance, no RSVP, no
mutations; those belong to slices 2-3.

## Core Components

### `EventsView` + `EventsViewModel`
- **EventsView** (`ios/Wishlist/Views/EventsView.swift`): lists events in
  `Upcoming` (date ascending) and `Past` sections; empty state "No events yet".
  A failed load surfaces an inline error row with a Retry button that calls
  `vm.load()`. Rows navigate to `EventDetailView` (:25-92).
- **EventsViewModel** (`ios/WishlistKit/ViewModels/EventsViewModel.swift`):
  `load()` → `client.events()` then partitions into `upcoming` /
  `past` by device-calendar day, **full-replacing** both arrays (:14-24).
  No optimistic updates.
- **EventDetailView** (`ios/Wishlist/Views/EventDetailView.swift`): header
  (name, full date, creator) plus the event's items rendered as `ItemRow`s;
  item rows reuse the masked `serialize_item(viewer)` view so an owner's own
  items never leak claim status.

### `WishlistEvent` + `APIClient` reads (WishlistKit)
- **WishlistEvent** (`ios/WishlistKit/Models/WishlistEvent.swift`): `id`,
  `name`, `date: Date` decoded from the `"YYYY-MM-DD"` string, `createdBy`
  lite struct (`{id, name}`), `itemCount`, and detail-only `items`.
  `isUpcoming` compares `Calendar.current.startOfDay(for: date)` against
  today's start-of-day — never a raw `Date()` comparison (IOS-EVT-005).
- **APIClient.events()** → `GET /api/v1/events` (`{events: [...]}`);
  **APIClient.event(id:)** → `GET /api/v1/events/<id>`
  (`{event, items:[serialize_item(viewer)]}`), following the existing
  `send`/envelope conventions. Detail items with absent `status` read as
  `isOwn` via the shared `Item` type.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| `[inferred]` Partition client-side by device-calendar day | `Calendar.current.startOfDay` boundary, today → upcoming | Trust server order as sections | Server orders ascending only; sections need a local day boundary (IOS-EVT-001/005). |
| `[inferred]` Detail items reuse `Item.isOwn` | Absent `status` → own | Separate event-item type | Same masked serializer; one surprise-protection rule, no drift (IOS-EVT-002). |
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

### Deferred
1. Event create/edit, RSVP/attendance tracking — needs server write access
   (slices 2-3).
2. Device-calendar sync (e.g. adding an event to the system calendar).

## References

- `docs/intent/boundary-ios/ios-events/ios-events-specs.md`
- Server mirror: `docs/API_V1.md` § Events
- Tests: `ios/WishlistKitTests/APIClientEventsTests.swift`, `ios/WishlistKitTests/EventsViewModelTests.swift`
- Code: `ios/Wishlist/Views/EventsView.swift`,
  `ios/Wishlist/Views/EventDetailView.swift`,
  `ios/WishlistKit/Models/WishlistEvent.swift`,
  `ios/WishlistKit/ViewModels/EventsViewModel.swift`
