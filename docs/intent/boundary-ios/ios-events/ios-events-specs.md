# ios-events EARS Specifications

- `[x]` **IOS-EVT-001**: The system shall fetch events via
  `GET /api/v1/events` and partition them into upcoming (date >= today,
  ascending) and past (date < today, descending); the Events tab shall render
  the two sections in that order.
- `[x]` **IOS-EVT-002**: When the user opens an event, the system shall fetch
  `GET /api/v1/events/<id>` and present the event plus its items, rendering
  each item row from the masked `serialize_item(viewer)` view (absent
  `status` → own item, no claim badges).
- `[x]` **IOS-EVT-003**: When the server returns no events, the system shall
  show an empty state ("No events yet"); the create affordance shall stay
  hidden (read-only slice 1).
- `[x]` **IOS-EVT-004**: When loading events fails, the system shall show
  "Couldn't load events." with a retry action that re-invokes `load()` and
  clears the error on success.
- `[x]` **IOS-EVT-005**: The system shall define the today boundary by the
  device-calendar day (`Calendar.current.startOfDay`) — an event dated today
  is upcoming; "upcoming" is never decided by a raw `Date()` comparison.
- `[x]` **IOS-EVT-006**: When the user taps + the system shall present a form (name required, date picker); on save it shall POST `/api/v1/events` `{name, date "YYYY-MM-DD"}` and on 201 insert the returned event into upcoming/past by device-calendar day; a validation failure shall surface the server message inline.
- `[x]` **IOS-EVT-007**: When the creator edits an event the system shall present the form prefilled (name + date); on save it shall PATCH `/api/v1/events/<id>` (partial) and on 200 replace the event in place, preserving list order.
- `[x]` **IOS-EVT-008**: When the creator deletes an event the system shall confirm ("items are kept, unlinked") then DELETE `/api/v1/events/<id>`; on 200 `{ok:true}` it shall remove the event from the list; linked items are kept, not deleted.
- `[x]` **IOS-EVT-009**: Edit/delete controls shall render only when `createdBy.id` equals the session user id; other viewers shall see no edit/delete affordance.
- `[x]` **IOS-EVT-010**: When a write fails the system shall surface a friendly error: 400 shows the server validation message, 403/404 shows a friendly error and reloads the list; the form stays open on 400 so edits are not lost.
