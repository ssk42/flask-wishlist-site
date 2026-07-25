# split-contributions LLD

## Core Concept
The **Split Contributions** feature allows multiple users (givers) to collaboratively fund an expensive wishlist item. One user initiates the process and becomes the "Organizer," moving the item from 'Available' to 'Splitting'. Other users can then join the split by pledging an amount. The item remains in the 'Splitting' state until the Organizer explicitly marks it as 'Purchased', at which point the Organizer takes credit for the purchase on behalf of the group.

## Data Models
- **`Contribution`**: Tracks individual pledges towards an item.
  - `item_id`, `user_id`: Links the contribution to a specific item and user.
  - `amount` (Float): The pledged dollar amount.
  - `is_organizer` (Boolean): Flag indicating if the user initiated the split or inherited the organizer role.
  - **Constraint**: `(item_id, user_id)` must be unique (a user can only have one active contribution record per item).
- **`Item` (computed properties)**:
  - `total_pledged`: Sum of all contribution amounts.
  - `remaining_amount`: `price - total_pledged` (bounded at 0).
  - `split_progress`: Percentage of the item funded (bounded at 100%).
  - `is_splitting`: Boolean helper checking if status is 'Splitting'.
  - `organizer`: The `User` object of the contribution with `is_organizer == True`.

## Components
- **`start_split` (Route)**: Transitions an 'Available' item to 'Splitting', creating an initial `Contribution` with `is_organizer=True`. Blocks the item's owner from splitting.
- **`join_split` (Route)**: Appends a new `Contribution` (`is_organizer=False`) to an item currently in the 'Splitting' state. Validates the user isn't already contributing.
- **`withdraw_contribution` (Route)**: Deletes a user's `Contribution`. If the deleted contribution was the last one, it reverts the item back to 'Available'. If the user was the organizer and others remain, the role is passed to the oldest remaining contributor.
- **`complete_split` (Route)**: Allowed only for the Organizer. Changes item status to 'Purchased' and sets `last_updated_by_id` to the Organizer's ID.
- **`_split_modal.html` & `_split_progress.html`**: UI layer showing funding progress, a list of contributors, and contextual forms to start, join, withdraw, or complete the split based on the current user's relationship to the item.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| **[inferred]** Unique constraint on `(item_id, user_id)` for contributions. | Allowing multiple contribution rows per user. | Simplifies queries, UI, and withdrawal logic by ensuring each user only has one pledge to manage. To increase a pledge, users effectively must withdraw and re-contribute (though no explicit update route exists). |
| **[inferred]** Allowing `complete_split` even if `remaining_amount > 0`. | Forcing 100% funding before purchase. | Prices are estimates. The organizer might cover the remaining balance out-of-pocket, or the actual purchase price might have been lower than expected. A warning is shown instead of a hard block. |
| **[inferred]** Reassigning the organizer role automatically on withdrawal. | Canceling the split entirely if the organizer leaves. | Prevents punishing other contributors if the original initiator decides to back out. The oldest contributor is the most logical next leader. |
| **[inferred]** Only the Organizer receives `last_updated_by_id` attribution. | Creating a multi-user attribution system. | Simplicity. It avoids rewriting the core item claiming logic. The Organizer is practically responsible for making the actual off-platform purchase using the pooled funds. |

## Open Questions
- **[inferred]** **Contribution Updates**: There is no direct route to "update" a contribution amount. A user must withdraw and rejoin, which causes an Organizer to lose their role if others are present.
- **[inferred]** **Overfunding Limits**: The UI allows input amounts up to `item.remaining_amount + 100`. This presumably accounts for tax and shipping, but it's an arbitrary hardcoded limit in the HTML rather than backend validation.
- **[inferred]** **Missing Notifications**: The `complete_split` route has a literal `# TODO: Send notifications to other contributors` comment. Currently, other contributors are not notified when the Organizer actually purchases the item.
