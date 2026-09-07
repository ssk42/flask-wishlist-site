# ios-curation LLD

## Context and Design Philosophy

`ios-curation` is the app surface where a user manages their own wishlist items:
view, add, edit, and delete their own list. It is the client mirror of the server's
`boundary-owner` / `item-curation` segment. Because items here are always the
viewer's own, the server sends **no** `status`/`lastUpdatedBy` — so this surface
never renders claim badges or gift actions.

## Core Components

### `MyListView` — `ios/Wishlist/Views/MyListView.swift`
Own-list tab. Builds `MyListViewModel(client:userID:)` with the logged-in user's id
from `session.state`; when built while logged out it renders a "log in" empty state
and never loads (no `userID: 0` fallback query). Binds `.searchable` to the view
model's `query` and renders `filteredItems`.
- `WLScreenTitle("My List")` with a `+` (plus.circle.fill) accessory opening the
  add sheet (:13-20).
- Rows are `ItemRow` in `wlCard`; tap → edit sheet; swipe-to-delete
  `.onDelete` → `vm.delete` per item (:73-77).
- Empty state: "Your list is empty" + "Tap + to add something you're wishing for."
- Pull-to-refresh (:90).

### `ItemEditView` — `ios/Wishlist/Views/ItemEditView.swift`
Shared add/edit form. `init(title:item:onSave:)`; `item == nil` → add, else edit
prefilled from `item`. Fields: description (required), link (URL keyboard,
autocorrect off), price (decimal), category, priority (Picker High/Medium/Low,
default Medium), and Options section (size, color, quantity). Save disabled when
description empty or saving (:59). Constructs an `ItemDraft`, `await onSave(draft)`,
dismisses on `true`. Blank strings → `nil` so PATCH stays partial.
Cascade: the form also reads the events list for an owner-only event picker (`event_id`, None = unlinked) — a one-way curation→events read, no co-ownership (IOS-EVT-012).

### `MyListViewModel` — `ios/WishlistKit/ViewModels/MyListViewModel.swift`
Holds `query: String` plus `selectedPriority/selectedCategory: String?` (nil =
All) and exposes `filteredItems` (description + category substring, case- and
diacritic-insensitive, AND both active filters; empty query and unset filters →
all; nil item fields match only All) — pure derivation, unit-tested (IOS-CUR-009,
IOS-CUR-011). No status filter exists on this surface (own items carry no
status). Category options are derived from the loaded items (distinct, sorted,
case-insensitive dedupe), not freeform.
- `load()` → `client.items(userID:)`.
- `create(_ draft) -> Bool`: `client.createItem`, INSERTS at index 0 (:26-40);
  exposes server validation message on 400.
- `update(id:_ patch) -> Bool`: `client.updateItem`, replaces in-place (:42-55).
- `delete(_ item)`: `client.deleteItem`, removes (:57-64).

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| `[inferred]` One shared `ItemEditView` for add and edit | Same form, `item` optional | Two forms | Fields identical; avoids drift. |
| `[inferred]` `create`/`update` return `Bool` | Bool success | Throwing / optimistic | Caller dismisses the sheet on `true`; validation message surfaced. |
| `[inferred]` Logged-out build renders a log-in empty state, never loads | Empty state | `userID: 0` fallback / crash | No query for a nonexistent user; no production crash on an impossible state. |
| `[inferred]` My List search covers description + category | Two fields | Description only | Category is user-visible list content; same cheap `contains`. |
| `[inferred]` Create inserts at index 0 | Prepend | Append | Newest-first matches dashboard convention. |
| `[inferred]` Blank form fields → `nil` before save | Partial payload | Send empty strings | PATCH persists only keys present; avoids writing empty strings. |
| `[inferred]` No status/gift actions on own items | Rely on absent status | Explicit hide | Server omits status for own items; client must not invent it. |
| `[inferred]` My List filters are priority + category only, no status | Two filters, no status UI | Status filter on own list | Own items always carry nil status, so a status filter would be dead UI. |
| `[inferred]` Category options derived from the loaded list | Distinct sorted present values | Freeform category entry | Category is free text server-side; a picker of present values can't select the empty set by typo. |

## Open Questions & Future Decisions

### Resolved
1. ✅ The design system (`Theme.swift`) is listed here because it is the shared
   dependency of every view segment; it is documented once and referenced, not
   owned pathologically by one feature.
2. ✅ Metadata prefill is available in `ItemEditView` — "Fetch details" fills empty
   description/price from the link's metadata via `MyListViewModel.prefill(url:)`
   (IOS-CUR-008); user-typed values are never clobbered.
3. ✅ Logged-out `MyListView` renders a log-in empty state and never loads — the
   `userID: 0` fallback is gone (IOS-CUR-010).

## References

- `docs/intent/boundary-ios/ios-curation/ios-curation-specs.md`
- Server mirror: `docs/intent/boundary-owner/item-curation.md`
- Tests: `ios/WishlistKitTests/MyListViewModelTests.swift`
- Code: `ios/Wishlist/Views/MyListView.swift`, `ios/Wishlist/Views/ItemEditView.swift`,
  `ios/WishlistKit/ViewModels/MyListViewModel.swift`,
  `ios/Wishlist/Theme.swift` (shared design system)