# owner-visibility LLD

## Core Concept
The "owner visibility" (also known as "surprise protection") boundary ensures that gift receivers cannot see the coordination activities happening around their own wishlist items. The system must prevent the item owner from knowing whether an item has been claimed, purchased, or split-funded, and must hide any coordination comments or status updates from them. This preserves the surprise of the gift while allowing other users (gift-givers) to collaborate effectively.

## Data Models
The implementation relies on comparing the current session's `current_user.id` against the `item.user_id` property.
There are no new tables introduced for this boundary, but it heavily influences how the `Item`, `Comment`, and `Contribution` data is rendered and serialized.

## Components
- **Item Cards/UI (`_item_card.html`, `_dashboard_item_card.html`, `_item_quick_view.html`)**: Conditionally renders badges (e.g. "Your Item" instead of "Claimed") and hides the "Last updated by" and "Claimed by" text when `current_user.id == item.user_id`. The quick-view modal's status fallback ("Item is …") is guarded with `item.user_id != current_user.id` so the owner never sees claim state (OWN-VIS-001). The dashboard route already excludes the owner's own items (`Item.user_id != current_user.id`), so dashboard cards only ever render giver-facing statuses.
- **Edit Item Form**: Hides the `status` dropdown and the current status when a user edits their own item.
- **Summary Table (`items.py` / `items_list` endpoint)**: The `At a Glance` summary totals exclude claimed/purchased items that belong to the current user (preventing mathematical deduction of claimed items).
- **Split Gifts (`_split_progress.html`)**: Hides the split progress bar and contribution amounts from the owner; they just see the item as normal and "Available".
- **Comments**: Hides the comments section on an item from its owner so givers can coordinate in secret.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| **[inferred]** Hiding state on the view layer rather than data layer | Creating separate DTOs or endpoints for owners vs givers. | Easier to implement in Flask templates using conditional logic (`if item.user_id != current_user.id`) rather than maintaining separate serialization logic. |
| **[inferred]** Returning "Available" for split gifts to the owner | Returning a generic "Hidden" status. | Returning "Available" makes the item appear completely normal and untouched, maximizing the surprise. |
| **[inferred]** Excluding own items from summary stats | Showing them but masking the counts. | Excluding them entirely prevents the user from mathematically deducing if one of their items was claimed by looking at total counts or sums. |

## Open Questions
- **[inferred]** If a user edits their item, could they accidentally overwrite a "Claimed" status back to "Available" since the status dropdown is hidden from them? Does the backend preserve the original status on edit?
- **[inferred]** Can a user infer if an item is claimed by sorting items by status in the items list view?
- **[inferred]** Are API endpoints (like those used for fetching metadata) returning the true status of an item to the owner, potentially leaking the surprise in the JSON payload?
