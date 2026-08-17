# ios-curation LLD

## Context and Design Philosophy

`ios-curation` is the app surface where a user manages their own wishlist items:
view, add, edit, and delete their own list. It is the client mirror of the server's
`boundary-owner` / `item-curation` segment. Because items here are always the
viewer's own, the server sends **no** `status`/`lastUpdatedBy` — so this surface
never renders claim badges or gift actions.

## Core Components

### `MyListView` — `ios/Wishlist/Views/MyListView.swift`
Own-list tab. Builds `MyListViewModel(client:userID:)`, deriving `userID` from
`session.state` at init (`.loggedIn(let u) → u.id`, else `0` fallback :11-14).
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

### `MyListViewModel` — `ios/WishlistKit/ViewModels/MyListViewModel.swift`
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
| `[inferred]` Create inserts at index 0 | Prepend | Append | Newest-first matches dashboard convention. |
| `[inferred]` Blank form fields → `nil` before save | Partial payload | Send empty strings | PATCH persists only keys present; avoids writing empty strings. |
| `[inferred]` No status/gift actions on own items | Rely on absent status | Explicit hide | Server omits status for own items; client must not invent it. |

## Open Questions & Future Decisions

### Resolved
1. ✅ The design system (`Theme.swift`) is listed here because it is the shared
   dependency of every view segment; it is documented once and referenced, not
   owned pathologically by one feature.
2. ✅ Metadata prefill is available in `ItemEditView` — "Fetch details" fills empty
   description/price from the link's metadata via `MyListViewModel.prefill(url:)`
   (IOS-CUR-008); user-typed values are never clobbered.

### Deferred
1. `userID` falls back to `0` if called while logged out — always guaranteed logged
   in in practice (tab only reachable when `.loggedIn`), but fragile; prefer
   unwrapping.

## References

- `docs/intent/boundary-ios/ios-curation/ios-curation-specs.md`
- Server mirror: `docs/intent/boundary-owner/item-curation.md`
- Tests: `ios/WishlistKitTests/MyListViewModelTests.swift`
- Code: `ios/Wishlist/Views/MyListView.swift`, `ios/Wishlist/Views/ItemEditView.swift`,
  `ios/WishlistKit/ViewModels/MyListViewModel.swift`,
  `ios/Wishlist/Theme.swift` (shared design system)