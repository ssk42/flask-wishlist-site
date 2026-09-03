# item-curation LLD

## Core Concept
The item curation boundary manages the lifecycle of a user's wishlist items. It ensures users can securely add, edit, archive, and delete their own items while restricting modification capabilities for non-owners. It employs idempotency tokens to handle duplicate form submissions safely. Archiving hides an item from every surface without destroying it; unarchiving restores it exactly.

## Data Models
- **Item**: Stores wishlist item metadata (description, link, price, category, image_url, priority, status, event_id, size, color, quantity, archived_at). Tied to a `user_id` (the owner). `archived_at` is null for active items and holds the archive timestamp otherwise; every item read excludes archived rows unless it is the Archived view.
- **Session state (`item_mutations`)**: Tracks a rolling buffer of the last 20 successful submission tokens to prevent duplicate requests.

## Components
- **Item Form Validation (`validate_item_fields`)**: Validates description length, HTTP URLs for links/images, positive prices, quantity bounds, and valid event IDs.
- **Idempotency Tracking (`_completed_submission`, `_remember_submission`)**: Tracks submission tokens in the session to prevent duplicate item creations/updates from repeated form submissions or accidental refreshes.
- **Owner Edit Protections (`edit_item`)**: Validates if `item.user_id == current_user.id`. Owners can edit all fields; non-owners can only update the item's status.
- **Item Deletion (`delete_item`)**: Strictly enforces owner-only deletion.
- **Archived State (`archive_item` / `unarchive_item`)**: Owner-only transitions that set or clear `archived_at`. Archiving preserves status, claims, contributions, comments, and price history untouched. Re-archiving an archived item or unarchiving an active item is a no-op with an informational flash. Action endpoints (claim, unclaim, status update, comment, contribute, refresh-price) reject archived items with a flash and redirect, mirroring the hidden-everywhere read model.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| **[inferred]** Idempotency via session tokens (`item_mutations`) | Relying solely on POST/Redirect/GET pattern | Prevents duplicate entries when users accidentally double-click submit or refresh a slow POST request. |
| **[inferred]** Non-owners can edit item status | Strict owner-only edits for all fields | Allows gift-givers to update the status (e.g. to Claimed or Purchased) from the edit page if they stumble into it. |
| Nullable `archived_at` timestamp for archive state | Boolean flag, or `Archived` as a status value | The timestamp preserves the item's status across restore and records when archiving happened at the same query cost as a boolean; a status value would destroy the prior status and collide with claim/split logic keyed on status strings. |

## Open Questions
- **[inferred]** The session token dictionary is capped at 20 entries (evicting oldest via insertion order). Could this cause issues for users making many edits quickly across multiple tabs?
- **[inferred]** Non-owners are allowed to access `/edit_item/<id>` but can only change the status. Should they be blocked entirely from the edit view and only be allowed to update status via a separate `claim_item` / status change route?
