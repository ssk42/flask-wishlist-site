# item-claiming LLD

## Core Concept
The item-claiming segment allows users (gift givers) to claim items from other users' wishlists to avoid duplicate gifts. It implements "surprise protection," ensuring that item owners cannot see who has claimed or purchased their own items. The segment also provides a "My Claims" view where users can track the items they've claimed or purchased for others, organized by recipient.

## Data Models
- **Item**:
  - `status`: String representing the state of the item (e.g., 'Available', 'Claimed', 'Purchased').
  - `user_id`: The ID of the user who owns the item.
  - `last_updated_by_id`: The ID of the user who most recently updated the item, which effectively acts as the "claimer" ID when an item's status transitions to 'Claimed'.
- **User**:
  - Contains information about the claimer or the item owner.

## Components
- **Claim Action (`claim_item`)**: Endpoint that allows a user to mark an 'Available' item as 'Claimed'. It updates `status` and `last_updated_by_id`.
- **Unclaim Action (`unclaim_item`)**: Endpoint that allows the user who claimed an item to revert its status back to 'Available'.
- **My Claims Page (`my_claims`)**: A dashboard for gift givers showing all items they have claimed or purchased. Groups the items by the item owner (recipient).
- **Navbar Badge**: Displays the count of currently claimed (but not yet purchased) items for the logged-in user.
- **Dashboard Widget**: Displays claimed and purchased counts when the user has active claims.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| **[inferred]** Using `last_updated_by_id` to track the claimer instead of a dedicated `claimed_by_id` field. | Creating a specific `claimed_by_id` foreign key. | Reusing the audit field simplifies the schema, though it couples audit history with business logic (claiming). |
| **[inferred]** Returning HTMX partials for claim/unclaim when requested via `HX-Request`. | Always redirecting back to the previous page. | HTMX provides a smoother, SPA-like user experience without full page reloads. |
| **[inferred]** Hiding claims from the item owner ("surprise protection"). | Showing all claims to everyone. | Essential for a wishlist application so the recipient's gift is not ruined. |

## Open Questions
- **[inferred]** Bug/Quirk: If another user edits an item (e.g., changes price) while it's claimed, `last_updated_by_id` might be overwritten, potentially re-assigning or losing the "claimer" record? The codebase seems to rely heavily on `last_updated_by_id` for ownership of the claim.
- **[inferred]** TODO marker about sending notifications to other contributors. Are notifications fully integrated into the claim workflow?
