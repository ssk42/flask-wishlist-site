---
status: OK
---

# ios-gifting Arrow

The gift-giver surface: family roster → member items → claim/unclaim/purchase, plus
the Claims tab. Client mirror of `boundary-giver`'s `item-claiming`.

## Artifacts
- **LLD**: [docs/intent/boundary-ios/ios-gifting.md](../../intent/boundary-ios/ios-gifting.md)
- **EARS Specs**: [docs/intent/boundary-ios/ios-gifting/ios-gifting-specs.md](../../intent/boundary-ios/ios-gifting/ios-gifting-specs.md)
- **Tests**: `ios/WishlistKitTests/FamilyViewModelTests.swift` (family + member-items
  view models), `ios/WishlistKitTests/ClaimsViewModelTests.swift`,
  `ios/WishlistKitTests/MemberItemsViewModelTests.swift` (member search + filters)
- **Code**: `ios/Wishlist/Views/FamilyView.swift`,
  `ios/Wishlist/Views/MemberItemsView.swift`,
  `ios/Wishlist/Views/ItemDetailView.swift`,
  `ios/Wishlist/Views/ClaimsView.swift`, `ios/Wishlist/Views/ItemRow.swift`,
  `ios/Wishlist/Views/FilterBar.swift` (shared filter menu),
  `ios/WishlistKit/TextSearch.swift` (shared substring matcher),
  `ios/WishlistKit/ViewModels/FamilyViewModel.swift`,
  `ios/WishlistKit/ViewModels/MemberItemsViewModel.swift`,
  `ios/WishlistKit/ViewModels/ClaimsViewModel.swift`

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| Browse   | IOS-GIFT-001, IOS-GIFT-002, IOS-GIFT-010 | 3 | 0 | 0 |
| Mutate   | IOS-GIFT-003 to IOS-GIFT-006 | 4 | 0 | 0 |
| Claims   | IOS-GIFT-007 to IOS-GIFT-009 | 3 | 0 | 0 |
| Filter   | IOS-GIFT-011 to IOS-GIFT-013 | 3 | 0 | 0 |

**Summary:** 13 of 13 active specs implemented.

## Key Findings

1. **Surprise protection is structural** — the whole Gift-status card renders only
   when `status` is non-nil (`ItemDetailView.swift:47-48`), i.e. another member's
   item; own items show no claim state.
2. **Mutations replace in place** from the server's returned item
   (`MemberItemsViewModel.swift:25-36`), keeping status authoritative.
3. **Server conflict codes map to copy** — `own_item`, `not_available`,
   `already_purchased`, `claimed_by_other` (`MemberItemsViewModel.swift:43-49`).
4. **Claims rows open the item detail** — the owner is resolved from the roster and
   the detail is presented via the shared full-screen cover (IOS-GIFT-009).
5. **Family roster search** — VM-held query, `filteredUsers` substring match
   (case/diacritic-insensitive), no-results state (IOS-GIFT-010). Claims failures
   route through the shared `ConflictCopy` instead of duplicated strings.
6. **Member-items search+filters, claims search+status** — all client-side and
   VM-held: query plus status/priority/category filters compose with AND in
   `filteredItems`, unset filters constrain nothing, no-matches render the
   no-results state (IOS-GIFT-011, IOS-GIFT-012, IOS-GIFT-013).

## Work Required

None blocking.