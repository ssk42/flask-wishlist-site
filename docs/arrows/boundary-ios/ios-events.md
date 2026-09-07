---
status: OK
---

# ios-events Arrow

The read-only Events surface: Events tab (upcoming/past), event detail with
masked item rows, and the `GET /api/v1/events` / `GET /api/v1/events/<id>`
client mirror.

## Artifacts
- **LLD**: [docs/intent/boundary-ios/ios-events.md](../../intent/boundary-ios/ios-events.md)
- **EARS Specs**: [docs/intent/boundary-ios/ios-events/ios-events-specs.md](../../intent/boundary-ios/ios-events/ios-events-specs.md)
- **Tests**: `ios/WishlistKitTests/APIClientEventsTests.swift`, `ios/WishlistKitTests/EventsViewModelTests.swift`
- **Code**: `ios/Wishlist/Views/EventsView.swift`,
  `ios/Wishlist/Views/EventDetailView.swift`,
  `ios/WishlistKit/Models/WishlistEvent.swift`,
  `ios/WishlistKit/ViewModels/EventsViewModel.swift`

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| Listing  | IOS-EVT-001, IOS-EVT-005 | 2 | 0 | 0 |
| Detail   | IOS-EVT-002 | 1 | 0 | 0 |
| States   | IOS-EVT-003, IOS-EVT-004 | 2 | 0 | 0 |

**Summary:** 5 of 5 active specs implemented.

## Key Findings

1. **Events are family-visible, partitioned locally** — the server returns all
   events ascending; the client splits upcoming/past by device-calendar day
   (`Calendar.current.startOfDay`, today → upcoming) (IOS-EVT-001/005).
2. **Detail rows reuse the masked item view** — `GET /api/v1/events/<id>`
   items are `serialize_item(viewer)`; absent `status` reads as own via the
   shared `Item.isOwn`, so no claim state can leak (IOS-EVT-002).
3. **Slice 1 hides creation** — the empty state ("No events yet") carries no
   create affordance (IOS-EVT-003).
4. **Failures show "Couldn't load events." with retry** — retry re-invokes
   `load()`, which full-replaces the lists and clears the error (IOS-EVT-004).

## Work Required

### Slices 2-3
1. Event create/edit + RSVP/attendance (needs server write contract).
2. Device-calendar sync and user-specific filtering.
