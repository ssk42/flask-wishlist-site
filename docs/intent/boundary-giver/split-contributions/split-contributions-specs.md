# split-contributions EARS Specifications

- [x] **GIV-SPL-001**: While an item is in the 'Available' state, IF a user (who is not the item owner) provides an initial contribution amount, THEN the system shall change the item's status to 'Splitting' and record the user's contribution with the `is_organizer` flag set to true.
- [x] **GIV-SPL-002**: While an item is in the 'Splitting' state, IF a user (who is not the item owner and is not already contributing) provides a contribution amount, THEN the system shall allow them to join the split and record their contribution with the `is_organizer` flag set to false.
- [x] **GIV-SPL-003**: While a user has an active contribution on an item, IF the user requests to withdraw their contribution, THEN the system shall delete their contribution record.
- [x] **GIV-SPL-004**: While an organizer withdraws their contribution, IF there are other remaining contributors, THEN the system shall automatically reassign the `is_organizer` flag to the remaining contributor with the oldest `created_at` timestamp.
- [x] **GIV-SPL-005**: While a user withdraws their contribution, IF it is the last remaining contribution for that item, THEN the system shall revert the item's status to 'Available'.
- [x] **GIV-SPL-006**: While an item is in the 'Splitting' state, IF the designated organizer requests to complete the split, THEN the system shall change the item's status to 'Purchased' and assign the organizer as the item's `last_updated_by_id`.
- [x] **GIV-SPL-007**: While a user attempts to complete a split, IF they are not the organizer, THEN the system shall reject the request and display an error message.
- [x] **GIV-SPL-008**: While an item's split state is accessed, THEN the system shall compute and expose the `total_pledged`, `remaining_amount`, and a `split_progress` percentage bounded at 100%.
