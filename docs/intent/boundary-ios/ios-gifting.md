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
  others). Rows are `ItemRow`; swipe actions on "Claimed": Unclaim (destructive) +
  Purchased (.wlGreen) (:28-34). No navigation to detail.
- **ItemRow** (`ItemRow.swift`): shared row; `StatusPill` renders only when
  `status != nil && status != "Available"` (:39-41) — so own items AND unclaimed
  others' items both show no pill.

### View models (WishlistKit, `ios/WishlistKit/ViewModels/`)
All `@MainActor @Observable`; `isLoading` flipped with single error string.
- **FamilyViewModel** (`FamilyViewModel.swift`): `load()` → `client.users()`.
- **MemberItemsViewModel** (`MemberItemsViewModel.swift`): `member: User` (let,
  :6); `load()` → `client.items(userID:)`; `claim`/`unclaim`/`purchase` funnel
  through `mutate(_:action:)` (:25-36) which runs the closure then REPLACES the
  item in the array. `friendly()` (:43-49) maps server conflict codes
  (`own_item`, `not_available`, `already_purchased`, `claimed_by_other`) to
  user-facing strings; other errors → "Action failed. Try again."
- **ClaimsViewModel** (`ClaimsViewModel.swift`): `load()` → `client.myClaims()`;
  `unclaim(_)` removes the item from the array (:21-28); `purchase(_)` replaces it
  in place (:31-38).

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| `[inferred]` Mutations replace the item in place from the server's returned payload | Replace-in-place | Local optimistic flip | Keeps status authoritative from the server; no drift. |
| `[inferred]` Gift card + actions hidden for own items (status nil) | Hide entire card | Show disabled actions | Preserves surprise protection; owner must not see claim state. |
| `[inferred]` Server conflict codes mapped to copy | `friendly()` map | Surface raw codes | User-facing messages for the four known server conflicts. |
| `[inferred]` `ItemRow` suppresses "Available" pill too | Only non-Available pills | Always show status | Declutters rows; "Available" is the default state. |

## Open Questions & Future Decisions

### Resolved
1. ✅ Tab count is four (Family, My List, Claims, Activity), not five — any doc
   claiming five is stale.
2. ✅ Claims rows are now tappable — the owner is resolved from the roster and the
   item detail is presented via the same full-screen cover as push deep links
   (IOS-GIFT-009).

### Deferred
1. `MemberItemsViewModel.mutate`'s `friendly(code:)` mapping is shared across
   claim/unclaim/purchase; `ClaimsViewModel` duplicates "Couldn't unclaim." /
   "Couldn't mark purchased." copy instead of reusing it. Consolidate the two
   error paths' copy when the Claims detail cover lands.

## References

- `docs/intent/boundary-ios/ios-gifting/ios-gifting-specs.md`
- Server mirror: `docs/intent/boundary-giver/item-claiming.md`
- Tests: `ios/WishlistKitTests/FamilyViewModelTests.swift` (covers
  `FamilyViewModel` and `MemberItemsViewModel` — no separate
  `MemberItemsViewModelTests` file)
- Code: `ios/Wishlist/Views/FamilyView.swift`, `ios/Wishlist/Views/MemberItemsView.swift`,
  `ios/Wishlist/Views/ItemDetailView.swift`, `ios/Wishlist/Views/ClaimsView.swift`,
  `ios/Wishlist/Views/ItemRow.swift`, `ios/WishlistKit/ViewModels/{Family,MemberItems,Claims}ViewModel.swift`