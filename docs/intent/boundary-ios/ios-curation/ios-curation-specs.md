# ios-curation EARS Specifications

- `[x]` **IOS-CUR-001**: The system shall load and display the current user's own
  wishlist items on the My List tab, newest first.
- `[x]` **IOS-CUR-002**: When the user adds an item, the system shall present the
  add form with fields description (required), link, price, category, priority, and
  options size/color/quantity, and on save shall POST the item and insert it at the
  top of the list.
- `[x]` **IOS-CUR-003**: When the user edits an item, the system shall prefill the
  form from the item and on save shall `PATCH` it, replacing the list entry with the
  server's returned item.
- `[x]` **IOS-CUR-004**: When the user swipe-deletes an item, the system shall issue
  `DELETE` and remove it from the list.
- `[x]` **IOS-CUR-005**: The add/edit form shall keep the Save action disabled while
  the description is empty or a save is in flight, and shall dismiss only on
  successful save.
- `[x]` **IOS-CUR-006**: When building a patch for an edit, the system shall send
  `nil` for blank optional fields so only present values are persisted.
- `[x]` **IOS-CUR-007**: The My List surface shall never render claim badges or
  gift actions for the user's own items (their `status` is absent from the server).
- `[x]` **IOS-CUR-008**: When the add/edit form shows a non-empty link and the user
  taps "Fetch details", the system shall best-effort prefill empty
  description/price fields from the link's metadata without clobbering user-typed
  values, and never block saving when the lookup fails.
- `[x]` **IOS-CUR-009**: When the user types in the My List search field, the
  system shall show only items whose description or category contains the query
  (case- and diacritic-insensitive); an empty query shall show the full list; a
  query with no matches shall show a no-results state distinct from the empty-list
  state. Deletion shall resolve by item id, not list index, so swipe-to-delete
  removes the intended item while filtered.
- `[x]` **IOS-CUR-010**: When the My List tab is built while logged out, the system
  shall render a log-in empty state and issue no items request.
- `[x]` **IOS-CUR-011**: When priority or category filters are set on My List,
  the system shall show only items matching ALL active filters AND the search
  query; unset filters shall constrain nothing; items with nil priority/category
  shall appear only when that filter is unset; no status filter shall exist on
  this surface (own items carry no status). Deletion while filtered shall resolve
  by item id. No matches shall show the no-results state.