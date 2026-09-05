# ios-gifting EARS Specifications

- `[x]` **IOS-GIFT-001**: The system shall load and display the family roster on
  the Family tab, each member with their name and item count, navigating to that
  member's items.
- `[x]` **IOS-GIFT-002**: When viewing another member's items, the system shall
  fetch them via `items(userID:)` and display each as an item row.
- `[x]` **IOS-GIFT-003**: When a user claims, unclaims, or purchases another
  member's item, the system shall call the corresponding endpoint and replace the
  item in the list with the server's returned item.
- `[x]` **IOS-GIFT-004**: When a claim/purchase fails with a server conflict code,
  the system shall map `own_item`, `not_available`, `already_purchased`, and
  `claimed_by_other` to user-facing messages.
- `[x]` **IOS-GIFT-005**: When viewing an item detail, the system shall render the
  "Gift status" card (status pill + claim/unclaim/purchase actions) only when the
  item has a non-nil `status` (i.e. the item belongs to someone else).
- `[x]` **IOS-GIFT-006**: When a gift status is `Available`, the system shall
  offer "Claim it" and "Mark purchased" actions; when `Claimed`, "Unclaim" and
  "Mark purchased"; when `Purchased`, no actions.
- `[x]` **IOS-GIFT-007**: The Claims tab shall list items the user has
  claimed/purchased for others, with swipe actions (unclaim, mark purchased) on
  items still `Claimed`.
- `[x]` **IOS-GIFT-008**: The item row shall show a status pill only when status is
  non-nil and not `"Available"`, so own items and unclaimed others' items render no
  pill.
- `[x]` **IOS-GIFT-009**: When the user taps a claim on the Claims tab, the system
  shall resolve the item's owner and present the item detail (same full-screen
  cover as a tapped push notification); if the roster can't be loaded it shall stay
  on the list.
- `[x]` **IOS-GIFT-010**: When the user types in the Family roster search field,
  the system shall show only members whose name contains the query (case- and
  diacritic-insensitive); an empty query shall show the full roster; a query with
  no matches shall show a no-results state, not an empty roster.
- `[x]` **IOS-GIFT-011**: When the user types in a member's items search field,
  the system shall show only items whose description or category contains the
  query (case- and diacritic-insensitive); an empty query shall show the full
  list; a query with no matches shall show a no-results state distinct from the
  empty-list state.
- `[x]` **IOS-GIFT-012**: When status, priority, or category filters are set on
  a member's items, the system shall show only items matching ALL active filters
  AND the search query; unset filters shall constrain nothing; items with a nil
  priority/category shall appear only when that filter is unset; a filter
  combination with no matches shall show the no-results state.
- `[x]` **IOS-GIFT-013**: When the user types in the Claims search field, the
  system shall show only claims whose description or category contains the query
  (case- and diacritic-insensitive); when a status filter (Claimed/Purchased) is
  set, it shall show only claims with that status; an empty query and unset
  filter shall show all claims; no matches shall show a no-results state
  distinct from the empty-claims state. Swipe actions and tap-to-detail shall
  operate on the filtered rows.