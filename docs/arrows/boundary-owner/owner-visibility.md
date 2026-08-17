---
status: AUDITED
---

# owner-visibility Arrow

## Artifacts
- **LLD**: [docs/intent/boundary-owner/owner-visibility.md](../../intent/boundary-owner/owner-visibility.md)
- **EARS Specs**: [docs/intent/boundary-owner/owner-visibility/owner-visibility-specs.md](../../intent/boundary-owner/owner-visibility/owner-visibility-specs.md)
- **Tests**: `tests/unit/test_surprise_protection.py`
- **Code**: `templates/partials/_item_card.html`,
  `templates/partials/_dashboard_item_card.html`,
  `templates/partials/_item_quick_view.html`,
  `templates/partials/_split_progress.html`,
  `templates/edit_item.html`, `blueprints/items.py` (summary totals, edit guards)

## Key Findings

1. **Surprise protection holds across surfaces** — item cards, dashboard cards
   (route-excluded for owners), edit form, comments, split progress, and now the
   quick-view modal (guard added 2026-08-16: status fallback requires
   `item.user_id != current_user.id`, OWN-VIS-001).
2. **Dashboard never renders the owner's own items** — `blueprints/dashboard.py:index`
   filters `Item.user_id != current_user.id`, so dashboard-card status is
   giver-facing only.
