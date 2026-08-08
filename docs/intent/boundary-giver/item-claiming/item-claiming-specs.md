# item-claiming EARS Specifications

- [x] **GIV-CLM-001**: While viewing an item, if the current user is the owner of the item, the system shall not display the claim button.
- [x] **GIV-CLM-002**: When a user attempts to claim their own item, the system shall reject the request and display a warning message.
- [x] **GIV-CLM-003**: When a user successfully claims an item, the system shall change the item's status to 'Claimed' and record the user as the claimer (via `last_updated_by_id`).
- [x] **GIV-CLM-004**: While an item is not in 'Available' status, the system shall prevent any user from claiming it.
- [x] **GIV-CLM-005**: When a user attempts to unclaim an item, if the item is 'Claimed' and the user is the one who claimed it, the system shall change the item's status back to 'Available'.
- [x] **GIV-CLM-006**: When a user attempts to unclaim an item they did not claim, the system shall reject the request and display an error message.
- [x] **GIV-CLM-007**: While a user views the 'My Claims' page, the system shall display a list of all items the user has claimed or purchased for others, grouped by the item owner.
- [x] **GIV-CLM-008**: While a user views the 'My Claims' page, the system shall exclude any items owned by the current user from the list.
- [x] **GIV-CLM-009**: When a user logs in and has claimed items, the system shall display a badge in the navbar indicating the total number of items currently in 'Claimed' status by that user.
- [x] **GIV-CLM-010**: While a request to claim or unclaim includes an HTMX header (`HX-Request`), the system shall return a partial item card response instead of a full page redirect.
- [x] **GIV-CLM-011**: While generating summary totals for an item, if the current user is the owner, the system shall exclude claimed and purchased statistics to preserve the surprise.
