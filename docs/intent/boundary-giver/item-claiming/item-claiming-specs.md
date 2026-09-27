# item-claiming EARS Specifications

- [x] **GIV-CLM-001**: While viewing an item, if the current user is the owner of the item, the system shall not display the claim button.
- [x] **GIV-CLM-002**: When a user attempts to claim their own item, the system shall reject the request and display a warning message.
- [x] **GIV-CLM-003**: When a user successfully claims an item, the system shall change the item's status to 'Claimed' and record the user as the claimer (via `last_updated_by_id`).
- [x] **GIV-CLM-004**: While an item is not in 'Available' status, the system shall prevent any user from claiming it.
- [x] **GIV-CLM-005**: When a user attempts to unclaim an item, if the item is 'Claimed' and the user is the one who claimed it, the system shall change the item's status back to 'Available'.
- [x] **GIV-CLM-006**: When a user attempts to unclaim an item they did not claim, the system shall reject the request and display an error message.
- [x] **GIV-CLM-007**: While a user views the 'My Claims' page, the system shall display a list of all items the user has claimed or purchased for others, grouped by the item owner.
- [x] **GIV-CLM-008**: While a user views the 'My Claims' page, the system shall exclude any items owned by the current user from the list.
- [x] **GIV-CLM-009**: When rendering an authenticated navbar, the system shall display a badge only when the viewer has unarchived Claimed items owned by other users and assigned to the viewer via last_updated_by_id, showing the count of those items.
- [x] **GIV-CLM-010**: While a request to claim or unclaim includes an HTMX header (`HX-Request`), the system shall return a partial item card response instead of a full page redirect.
- [x] **GIV-CLM-011**: While generating summary totals for an item, if the current user is the owner, the system shall exclude claimed and purchased statistics to preserve the surprise.

- [x] **GIV-CLM-012**: When calculating a web claim summary for a viewer, the system shall count only unarchived items owned by another user whose last_updated_by_id equals that viewer, returning separate Claimed and Purchased counts with integer zero for absent statuses and counting qualifying completed split items once for their organizer without adding contribution rows.
- [x] **GIV-CLM-013**: When a web request needs a viewer's claim summary without a reusable result, the system shall obtain both status counts in one grouped aggregate query and reuse that result for the same viewer within that request until invalidated.
- [x] **GIV-CLM-014**: When My Claims loads its complete unpaginated claim collection after pending ORM writes are flushed, the system shall replace the viewer's request summary with counts derived from that collection, including zeros when empty, without an additional count query; filtered or paginated collections shall not seed the summary.
- [x] **GIV-CLM-015**: If item status, archive state, deletion, owner, or last updater changes after a web request has read a claim summary, the system shall invalidate affected viewer summaries before reuse and calculate subsequent summaries from current ORM state; rollback and bulk writes affecting the population shall also invalidate reuse, including both old and new viewers after reassignment.
- [x] **GIV-CLM-016**: When rendering a dashboard cache miss, the system shall use the same request claim summary for its widgets and navbar while preserving the existing per-user 60-second response cache policy.
- [x] **GIV-CLM-017**: When loading My Claims, the system shall batch collection relationships and eagerly load scalar owners and authors needed by rendering, preserving recipient grouping, item ordering, and the separate split-contribution list without per-item relationship queries.
