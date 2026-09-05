# ios-gifting LLD

## Context and Design Philosophy

`ios-gifting` is the gift-giver's coordination surface in the app: browse the
family roster, view another member's items, claim/unclaim/purchase on their behalf,
and track one's own claims. It is the client mirror of the server's `boundary-giver`
and its key invariant — coordination among givers that must never leak to the item
owner. The client enforces this by rendering claim state only where the server
sent it (`status` is non-`nil` only for others' items); the owner's own items show
no badge and no gift actions.

## Core Components

### Screens (app target, `ios/Wishlist/Views/`)
- **FamilyView** (`FamilyView.swift`): roster. Loads `FamilyViewModel.users`, renders
  member cards (Monogram, name, item count), `NavigationLink(value: User)` →
  `MemberItemsView`. Pull-to-refresh (:27, :39).
- **Family search**: `FamilyViewModel` holds the query (`query: String`) and exposes
  `filteredUsers` (name substring, case- and diacritic-insensitive; empty query →
  all). `FamilyView` binds `.searchable` to the query and renders `filteredUsers`.
  Query lives in the view model — not local view state — so filtering stays
  offline-testable in WishlistKit alongside `load()`.
- **MemberItemsView** (`MemberItemsView.swift`): one member's items. Injects a
  `MemberItemsViewModel(client:member:)`. Rows are `ItemRow` in `wlCard`,
  `NavigationLink(value: Item)` → `ItemDetailView` (:32-34).
- **ItemDetailView** (`ItemDetailView.swift`): reads `item` immutably but re-resolves
  `current` live from `vm.items` by id (:9) so claim/purchase reflects immediately.
  Header card (description, price, priority, category), variants
  (size/color/quantity only if present), external "View product" `Link`. The "Gift
  status" card with `StatusPill` + action buttons renders **only when `status` is
  non-nil** (:47-48, :60-73) — i.e. only for others' items. Actions by status
  (:82-94): Available → "Claim it" (primary) + "Mark purchased" (secondary);
  Claimed → "Unclaim" (secondary) + "Mark purchased" (primary); Purchased → none.
- **ClaimsView** (`ClaimsView.swift`): my claims (items claimed/purchased for
  others). Rows are tappable `ItemRow`s — tap resolves the owner from the roster
  and presents the item detail via the same full-screen `DeepLinkDetailView` cover
  as push deep links (IOS-GIFT-009); roster-unavailable → stay on the list. Swipe
  actions on "Claimed": Unclaim (destructive) + Purchased (.wlGreen) (:28-34).
- **ItemRow** (`ItemRow.swift`): shared row; `StatusPill` renders only when
  `status != nil && status != "Available"` (:39-41) — so own items AND unclaimed
  others' items both show no pill.

### View models (WishlistKit, `ios/WishlistKit/ViewModels/`)
All `@MainActor @Observable`; `isLoading` flipped with single error string.
- **FamilyViewModel** (`FamilyViewModel.swift`): `load()` → `client.users()`. Holds
  `query: String` and exposes `filteredUsers` (name substring, case- and
  diacritic-insensitive; empty query → all) — pure derivation, unit-tested
  (IOS-GIFT-010).
- **MemberItemsViewModel** (`MemberItemsViewModel.swift`): `member: User` (let,
  :6); `load()` → `client.items(userID:)`; `claim`/`unclaim`/`purchase` funnel
  through `mutate(_:action:)` (:25-36) which runs the closure then REPLACES the
  item in the array. `friendly()` (:43-49) maps server conflict codes
  (`own_item`, `not_available`, `already_purchased`, `claimed_by_other`) to
  user-facing strings; other errors → "Action failed. Try again." Holds `query:
  String` plus `selectedStatus/selectedPriority/selectedCategory: String?`
  (nil = All) and exposes one combined `filteredItems`: `TextSearch` query over
  description+category AND each active filter; nil item fields match only All.
  `load`/mutations unchanged (replace-in-place by id, so a claim/purchase under
  an active status filter removes the row from view immediately).
  Unit-tested (IOS-GIFT-011, IOS-GIFT-012). Filters reset on re-entry (fresh VM
  per push, matching query-today behavior).
- **ClaimsViewModel** (`ClaimsViewModel.swift`): `load()` → `client.myClaims()`;
  `unclaim(_)` removes the item from the array (:21-28); `purchase(_)` replaces it
  in place (:31-38). Failure copy reuses the shared `friendly()` mapping (one pure
  function in WishlistKit; both gift view models call it) instead of duplicating
  strings. Holds `query: String` plus `selectedStatus: String?` (nil = All, else
  Claimed/Purchased) and exposes `filteredItems` (query AND status).
  Unit-tested (IOS-GIFT-013). Scope is search+status only — priority/category
  deferred as low-signal on a cross-member action list.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| `[inferred]` Mutations replace the item in place from the server's returned payload | Replace-in-place | Local optimistic flip | Keeps status authoritative from the server; no drift. |
| `[inferred]` Gift card + actions hidden for own items (status nil) | Hide entire card | Show disabled actions | Preserves surprise protection; owner must not see claim state. |
| `[inferred]` One shared conflict-code→copy function for gift mutations | Shared pure function | Per-VM strings | Single copy source; unit-tested once. |
| `[inferred]` Search query lives in the view model, filter is derived | VM query + `filteredUsers` | Local `@State` filter | Keeps filtering offline-testable in WishlistKit; view stays a binding. |
| `[inferred]` `ItemRow` suppresses "Available" pill too | Only non-Available pills | Always show status | Declutters rows; "Available" is the default state. |
| `[inferred]` All item filtering is client-side over the loaded list | VM-held `query` + filters, one derived `filteredItems` | Server `q`/`status`/`category` params | Server `q` is description-only, `category` exact-only, no `priority` param, and `status` carries surprise-protection side conditions; client-side stays offline-testable and keystroke-instant. |
| `[inferred]` Received/Splitting visible under All only | Closed filter triple (Available/Claimed/Purchased) + All | One option per server status | Filter offers the giver-actionable states; other server statuses remain visible only when no status filter is set. |
| `[inferred]` Claims scope is search + status only | Query + `selectedStatus` | Priority/category filters on Claims | Cross-member action list; status is the task affordance, priority/category add no signal. |
| `[inferred]` Mutations under an active filter vanish immediately | Filtered-out rows disappear on replace-in-place | Preserve stale row until filter clears | Replace-in-place by id is the shipped mutation rule; a claim/purchase that moves an item across the active status filter removes it from view at once. |
| `[inferred]` Filters reset on re-entry | Fresh VM per push | Persist filters across visits | Matches query-today behavior; no cross-visit filter state to reconcile. |

## Open Questions & Future Decisions

### Resolved
1. ✅ Tab count is four (Family, My List, Claims, Activity), not five — any doc
   claiming five is stale.
2. ✅ Claims rows are now tappable — the owner is resolved from the roster and the
   item detail is presented via the same full-screen cover as push deep links
   (IOS-GIFT-009).
3. ✅ Claims error copy consolidated onto the shared `friendly()` mapping — one
   copy source for claim/unclaim/purchase failures across gift view models.

## References

- `docs/intent/boundary-ios/ios-gifting/ios-gifting-specs.md`
- Server mirror: `docs/intent/boundary-giver/item-claiming.md`
- Tests: `ios/WishlistKitTests/FamilyViewModelTests.swift` (covers
  `FamilyViewModel` and member claim mutations) and
  `ios/WishlistKitTests/MemberItemsViewModelTests.swift` (member search +
  filters, IOS-GIFT-011/012) plus `ClaimsViewModelTests.swift` (IOS-GIFT-013)
- Code: `ios/Wishlist/Views/FamilyView.swift`, `ios/Wishlist/Views/MemberItemsView.swift`,
  `ios/Wishlist/Views/ItemDetailView.swift`, `ios/Wishlist/Views/ClaimsView.swift`,
  `ios/Wishlist/Views/ItemRow.swift`, `ios/WishlistKit/ViewModels/{Family,MemberItems,Claims}ViewModel.swift`