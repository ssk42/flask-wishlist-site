# item-curation EARS Specifications

- [x] **OWN-ITEM-001**: When a user submits the create item form, if the submission token is already recorded in the session, the system shall flash an info message and redirect to the items list.
- [x] **OWN-ITEM-002**: When the owner of an item submits an edit request, the system shall update all provided fields (description, link, price, category, image_url, priority, event_id, size, color, quantity).
- [x] **OWN-ITEM-003**: When a non-owner submits an edit request for an item, the system shall only update the item's status and ignore other fields.
- [x] **OWN-ITEM-004**: When a user attempts to delete an item, if the user is not the owner, the system shall abort the deletion and flash an error message.
- [x] **OWN-ITEM-005**: When a user submits an item with a description longer than 750 characters, the system shall reject the submission with a validation error.
- [x] **OWN-ITEM-006**: When a user submits an item with a negative price, the system shall reject the submission with a validation error.
- [x] **OWN-ITEM-007**: When a user submits an item with a quantity less than 1 or greater than 99, the system shall reject the submission with a validation error.
- [x] **OWN-ITEM-008**: When a user submits an item with a link or image URL, if it is not an absolute HTTP or HTTPS URL, the system shall reject the submission with a validation error.
- [x] **OWN-ITEM-009**: When the owner of an item submits an archive request, the system shall set the item's `archived_at` to the current time, flash a confirmation, and redirect preserving active list filters.
- [x] **OWN-ITEM-010**: When a user attempts to archive or unarchive an item they do not own, the system shall abort the transition and flash an error message.
- [x] **OWN-ITEM-011**: When the owner of an archived item submits an unarchive request, the system shall clear `archived_at` and restore the item with its status, claims, contributions, comments, and price history unchanged.
- [x] **OWN-ITEM-012**: While rendering the items list, dashboard, summary totals, search results, My Claims, event item pickers, and API v1 responses, the system shall exclude items whose `archived_at` is not null; archived items appear only in the owner's Archived view.
- [x] **OWN-ITEM-013**: When a claim, unclaim, status update, comment, contribution, or price-refresh request targets an archived item, the system shall reject the action, flash an archived notice, and redirect.
- [x] **OWN-ITEM-014**: When the owner edits an archived item, the system shall apply the edit and leave the item archived.
- [x] **OWN-ITEM-015**: When selecting items for automatic price updates, the system shall exclude items whose `archived_at` is not null.
- [x] **OWN-ITEM-016**: When the owner selects the Archived status filter, the system shall list only that owner's archived items with Unarchive and Delete actions.
- [x] **OWN-ITEM-017**: When an archive request targets an already-archived item, or an unarchive request targets an active item, the system shall leave the item unchanged and flash an informational message.
