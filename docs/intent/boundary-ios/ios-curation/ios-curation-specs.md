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