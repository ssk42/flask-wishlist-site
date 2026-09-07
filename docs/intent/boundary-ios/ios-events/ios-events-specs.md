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
