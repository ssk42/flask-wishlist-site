---
status: OK
---

# ios-curation Arrow

The own-list management surface: view, add, edit, delete the user's own wishlist
items. Client mirror of `boundary-owner`'s `item-curation`.

## Artifacts
- **LLD**: [docs/intent/boundary-ios/ios-curation.md](../../intent/boundary-ios/ios-curation.md)
- **EARS Specs**: [docs/intent/boundary-ios/ios-curation/ios-curation-specs.md](../../intent/boundary-ios/ios-curation/ios-curation-specs.md)
- **Tests**: `ios/WishlistKitTests/MyListViewModelTests.swift`
- **Code**: `ios/Wishlist/Views/MyListView.swift`, `ios/Wishlist/Views/ItemEditView.swift`,
  `ios/WishlistKit/ViewModels/MyListViewModel.swift`,
  `ios/Wishlist/Theme.swift` (shared design system)

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| CRUD     | IOS-CUR-001 to IOS-CUR-008 | 8 | 0 | 0 |

**Summary:** 8 of 8 active specs implemented.

## Key Findings

1. **Shared add/edit form** — one `ItemEditView` with `item` optional; blank optional
   fields become `nil` so `PATCH` persists only present values.
2. **No claim state on own items** — the server omits `status`; the surface never
   renders badges/actions (IOS-CUR-007).
3. **Metadata prefill in the form** — "Fetch details" fills empty description/price
   from the link's metadata via `MyListViewModel.prefill(url:)`, never clobbering
   user input (IOS-CUR-008).
4. **`Theme.swift` is listed here** as the shared dependency of all view segments,
   documented once at this segment.

## Work Required

### Nice to Have
1. Replace the `userID` `0` fallback with an unwrap (reachable only when logged in).