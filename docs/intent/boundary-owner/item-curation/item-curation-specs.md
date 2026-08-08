# item-curation EARS Specifications

- [x] **OWN-ITEM-001**: When a user submits the create item form, if the submission token is already recorded in the session, the system shall flash an info message and redirect to the items list.
- [x] **OWN-ITEM-002**: When the owner of an item submits an edit request, the system shall update all provided fields (description, link, price, category, image_url, priority, event_id, size, color, quantity).
- [x] **OWN-ITEM-003**: When a non-owner submits an edit request for an item, the system shall only update the item's status and ignore other fields.
- [x] **OWN-ITEM-004**: When a user attempts to delete an item, if the user is not the owner, the system shall abort the deletion and flash an error message.
- [x] **OWN-ITEM-005**: When a user submits an item with a description longer than 750 characters, the system shall reject the submission with a validation error.
- [x] **OWN-ITEM-006**: When a user submits an item with a negative price, the system shall reject the submission with a validation error.
- [x] **OWN-ITEM-007**: When a user submits an item with a quantity less than 1 or greater than 99, the system shall reject the submission with a validation error.
- [x] **OWN-ITEM-008**: When a user submits an item with a link or image URL, if it is not an absolute HTTP or HTTPS URL, the system shall reject the submission with a validation error.
