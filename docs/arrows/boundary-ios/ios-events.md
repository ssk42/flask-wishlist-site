---
status: OK
---

# ios-events Arrow

The Events surface: Events tab (upcoming/past), event detail with
masked item rows, creator-side create/edit/delete, item↔event association
(owner-side picker), `/events/<id>` deep links, and the
`GET /api/v1/events` / `GET /api/v1/events/<id>` / `POST /api/v1/events` /
`PATCH` / `DELETE /api/v1/events/<id>` client mirror.

- **LLD**: [docs/intent/boundary-ios/ios-events.md](../../intent/boundary-ios/ios-events.md)
- **EARS Specs**: [docs/intent/boundary-ios/ios-events/ios-events-specs.md](../../intent/boundary-ios/ios-events/ios-events-specs.md)
- **Tests**: `ios/WishlistKitTests/APIClientEventsTests.swift`, `ios/WishlistKitTests/EventsViewModelTests.swift`,
  `ios/WishlistKitTests/ItemLinkTests.swift`, `ios/WishlistKitTests/APIClientWriteTests.swift`
- **Code**: `ios/Wishlist/Views/EventsView.swift`,
  `ios/Wishlist/Views/EventDetailView.swift`,
  `ios/Wishlist/Views/EventFormView.swift`,
  `ios/Wishlist/Views/ItemEditView.swift`,
  `ios/Wishlist/Views/MyListView.swift`,
  `ios/Wishlist/Views/RootTabView.swift`,
  `ios/Wishlist/Views/ActivityView.swift`,
  `ios/WishlistKit/Models/WishlistEvent.swift`,
  `ios/WishlistKit/Networking/APIClient.swift`,
  `ios/WishlistKit/Networking/ItemDraft.swift`,
  `ios/WishlistKit/TextSearch.swift` (`ItemLink`),
  `ios/WishlistKit/Intents/OpenTarget.swift`,
  `ios/WishlistKit/ViewModels/EventsViewModel.swift`

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| Listing  | IOS-EVT-001, IOS-EVT-005 | 2 | 0 | 0 |
| Detail   | IOS-EVT-002, IOS-EVT-011 | 2 | 0 | 0 |
| States   | IOS-EVT-003, IOS-EVT-004 | 2 | 0 | 0 |
| Writes   | IOS-EVT-006, IOS-EVT-007, IOS-EVT-008, IOS-EVT-009, IOS-EVT-010 | 5 | 0 | 0 |
| Association | IOS-EVT-012 | 1 | 0 | 0 |
| Deep links | IOS-EVT-013 | 1 | 0 | 0 |
| Contract | IOS-EVT-014 | 1 | 0 | 0 |

**Summary:** 14 of 14 active specs implemented.

## Key Findings

1. **Events are family-visible, partitioned locally** — the server returns all
   events ascending; the client splits upcoming/past by device-calendar day
   (`Calendar.current.startOfDay`, today → upcoming) (IOS-EVT-001/005).
2. **Detail rows reuse the masked item view** — `GET /api/v1/events/<id>`
   items are `serialize_item(viewer)`; absent `status` reads as own via the
   shared `Item.isOwn`, so no claim state can leak (IOS-EVT-002).
3. **Slice 1 hid creation; slice 2 adds it** — the empty state
   ("No events yet") carried no create affordance in slice 1 (IOS-EVT-003);
   slice 2 adds the `+` button + `EventFormView` sheet (IOS-EVT-006).
4. **Failures show "Couldn't load events." with retry** — retry re-invokes
   `load()`, which full-replaces the lists and clears the error (IOS-EVT-004).
5. **Writes are creator-gated, full-replace, last-write-wins** — edit/delete
   render only when `createdBy.id == session user id` (IOS-EVT-009); create
   inserts by day, update drops + re-inserts, delete removes the row while
   items are kept unlinked (IOS-EVT-006/007/008); 400 surfaces the server
   message, 403/404 reloads then shows a friendly error, no conflict UI
   (IOS-EVT-010).
6. **One-way curation→events dependency** — `MyListView` reads the events list
   for the item form's picker; events views never import curation, so neither
   list drives the other's state. The picker is owner-only (`ItemEditView`
   serves own items alone) and hides when the list is empty; save persists
   `event_id` via the existing item contract, None means nil/unlinked and
   omitted (IOS-EVT-012).
7. **Shared parser, no-drift rule** — `ItemLink.eventID(from:)` sits next to
   `itemID(from:)`; push taps (`RootTabView.route` → Events tab + pending id)
   and in-app taps (`ActivityView` re-posts through the push channel) share
   the one parser, and `EventsView` consumes the pending id once loaded,
   mirroring `FamilyView`'s pending-owner binding (IOS-EVT-013).
8. **Archived exclusion is server-side only** — counts and detail arrive
   pre-filtered; the client never filters (IOS-EVT-014). Event-detail taps
   reuse the existing `DeepLinkDetailView` cover with masked rows, so no
   claim UI can appear (IOS-EVT-011).

## Work Required

None blocking. Deferred: RSVP/attendance tracking, device-calendar sync.
