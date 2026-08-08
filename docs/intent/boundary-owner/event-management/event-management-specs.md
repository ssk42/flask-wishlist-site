# EARS Specifications - Event Management

## Event CRUD Specs
- [x] **OWN-EVT-001**: While a user is logged in, they shall be able to view a list of all events, divided into upcoming and past events.
- [x] **OWN-EVT-002**: When a logged-in user submits a valid event creation form with a name and date, the system shall create a new event associated with their user account.
- [x] **OWN-EVT-003**: When a user attempts to edit an event they created, they shall be allowed to update its name and date.
- [x] **OWN-EVT-004**: If a user attempts to edit or delete an event created by another user, the system shall flash a danger message and redirect them back to the events list.
- [x] **OWN-EVT-005**: When an event is deleted, the system shall set the `event_id` of all associated items to `None` before removing the event, preventing orphan errors and preserving the items.

## Event Reminders Specs
- [x] **OWN-EVT-006**: When an event is exactly 7 days away from the current date and its `reminder_sent` flag is False, the background task shall identify all items for that event that are 'Claimed' or 'Purchased'.
- [x] **OWN-EVT-007**: When processing claimed items for a reminder, the system shall group them by the user who claimed them (`last_updated_by_id`), excluding items where the claimer is the item owner.
- [x] **OWN-EVT-008**: For each claimer identified in the reminder task, the system shall send an email summarizing their claimed items and providing links to the items.
- [x] **OWN-EVT-009**: After the system processes all claimers for an event's reminder, it shall set the event's `reminder_sent` flag to True to prevent duplicate reminders on subsequent runs.
