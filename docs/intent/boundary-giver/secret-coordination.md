# secret-coordination LLD

## Core Concept
Secret coordination allows multiple family members to organize gift purchases while shielding the wishlist owner from spoilers. This segment establishes a one-way visibility boundary ("Surprise Protection"): users have full visibility into the claim status, split contributions, and discussion threads of *others'* items, but are systematically blinded to those same details for their *own* items.

## Data Models
- `Comment`: Associated with an `Item` and authored by a `User`. Holds the discussion text for coordination.
- `Notification`: Alerts a `User` when coordination events happen (e.g., new comments). Contains a `message`, `link`, and `is_read` flag.
- `Contribution`: Tracks users who are contributing to a split purchase.

## Components
- `blueprints/social.py`: Handles comment submission (`/item/<id>/comment`) and notification management. Enforces that item owners cannot participate in discussions on their own items.
- `blueprints/items.py`: 
  - Implements summary totals calculation with surprise protection (filters out the user's own claimed/purchased items).
  - Handles claiming, unclaiming, and split-gift lifecycle management.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| **[inferred]** Synchronous Notification Generation | Offloading notification generation to a background task (Celery). | Simpler architecture. Generating notifications for previous commenters requires minimal DB inserts and is fast enough to run in the request lifecycle (`social.py` L33-47). |
| **[inferred]** Python-level filtering for Surprise Protection | Complex SQL query filtering during aggregation. | Easier to maintain and reason about. Items are iterated and filtered in Python (`items.py` L184-188) when calculating summary totals. |
| **[inferred]** Notification Recipients | Notifying everyone in the family or just the organizer. | Notifying only previous commenters limits noise, creating opt-in discussion threads for specific items. |

## Open Questions
- **[inferred]** Contributor notification on split completion: `complete_split`
  notifies every other contributor (excluding the organizer and the item owner)
  via `create_notification` (GIV-SEC-007).
- **[inferred]** Do notifications auto-delete after a certain period, or will the `Notification` table grow unbounded over time?
- **[inferred]** If an item is unclaimed or deleted, what happens to the associated coordination comments? (Assuming cascade deletes, but worth verifying).
