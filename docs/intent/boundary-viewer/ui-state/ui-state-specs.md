# ui-state EARS Specifications

- [x] **VW-UI-001**: While viewing a list, if a user submits a request containing new filter parameters, the system shall save those filter parameters to the user's session.
- [x] **VW-UI-002**: When checking a request for new filter parameters, if the request provides only empty parameter values (e.g., `?status_filter=`), the system shall not overwrite the existing saved session filters.
- [x] **VW-UI-003**: If a request to the filtered list includes the parameter `clear_filters=true`, the system shall purge all saved filter parameters from the user's session.
- [x] **VW-UI-004**: When returning a user to a list view after an action (e.g., editing an item), the system shall automatically append the current active filters from the session to the redirect URL.
- [x] **VW-UI-005**: When an application process requires sending user feedback prior to a redirect, the system shall enqueue the flash message and execute the redirect via a combined view helper to reduce duplication.

- [x] **VW-UI-006**: When preparing template context, the system shall expose navigation badge helpers without executing claim or unread-notification count queries; rendering a template without the sidebar shall execute no navigation count queries.
- [x] **VW-UI-007**: When rendering an authenticated sidebar, the system shall evaluate each badge helper once, use the item-claiming request summary for claims, and count unread notifications only where user_id equals the viewer and is_read is false.
- [x] **VW-UI-008**: When an anonymous render or anonymous badge-helper call occurs, the system shall return zero badge counts without querying either badge population.
- [x] **VW-UI-009**: While a web request reuses badge values, the system shall isolate those values by viewer and request, discard them at request end, and introduce no cookie or cross-request badge cache; cached full responses shall retain their existing cache policy.
- [x] **VW-UI-010**: When the complete notification list is loaded after pending ORM writes are flushed, the system shall replace that viewer's request unread count with the number of unread rows, including zero for an empty list, without an extra unread-count query; filtered or paginated lists shall not seed the count.
- [x] **VW-UI-011**: If read state, notification creation/deletion, or recipient changes after a request has read an unread count, the system shall invalidate affected viewer counts before reuse and calculate subsequent counts from current ORM state; rollback and bulk writes affecting the population shall also invalidate reuse, including both old and new viewers after reassignment.
