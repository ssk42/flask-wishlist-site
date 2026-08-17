# item-curation LLD

## Core Concept
The item curation boundary manages the lifecycle of a user's wishlist items. It ensures users can securely add, edit, and delete their own items while restricting modification capabilities for non-owners. It employs idempotency tokens to handle duplicate form submissions safely.

## Data Models
- **Item**: Stores wishlist item metadata (description, link, price, category, image_url, priority, status, event_id, size, color, quantity). Tied to a `user_id` (the owner).
- **Session state (`item_mutations`)**: Tracks a rolling buffer of the last 20 successful submission tokens to prevent duplicate requests.

## Components
- **Item Form Validation (`validate_item_fields`)**: Validates description length, HTTP URLs for links/images, positive prices, quantity bounds, and valid event IDs.
- **Idempotency Tracking (`_completed_submission`, `_remember_submission`)**: Tracks submission tokens in the session to prevent duplicate item creations/updates from repeated form submissions or accidental refreshes.
- **Owner Edit Protections (`edit_item`)**: Validates if `item.user_id == current_user.id`. Owners can edit all fields; non-owners can only update the item's status.
- **Item Deletion (`delete_item`)**: Strictly enforces owner-only deletion.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| **[inferred]** Idempotency via session tokens (`item_mutations`) | Relying solely on POST/Redirect/GET pattern | Prevents duplicate entries when users accidentally double-click submit or refresh a slow POST request. |
| **[inferred]** Non-owners can edit item status | Strict owner-only edits for all fields | Allows gift-givers to update the status (e.g. to Claimed or Purchased) from the edit page if they stumble into it. |

## Open Questions
- **[inferred]** The session token dictionary is capped at 20 entries (evicting oldest via insertion order). Could this cause issues for users making many edits quickly across multiple tabs?
- **[inferred]** Non-owners are allowed to access `/edit_item/<id>` but can only change the status. Should they be blocked entirely from the edit view and only be allowed to update status via a separate `claim_item` / status change route?
