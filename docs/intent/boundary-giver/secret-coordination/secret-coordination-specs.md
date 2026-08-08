# secret-coordination EARS Specifications

- [x] **GIV-SEC-001**: While calculating summary totals, the system shall exclude the user's own claimed or purchased items from the counts and price totals to preserve surprise.
- [x] **GIV-SEC-002**: If a user attempts to submit a comment on an item they own, the system shall reject the submission and display a warning flash message.
- [x] **GIV-SEC-003**: When a user adds a comment to an item, the system shall generate a notification for all previous commenters on that item.
- [x] **GIV-SEC-004**: While generating comment notifications, the system shall exclude the item's owner and the current commenter from the recipient list.
- [x] **GIV-SEC-005**: When a user views their notifications, the system shall display them ordered by creation date descending.
- [x] **GIV-SEC-006**: When a user marks a notification as read, the system shall update the `is_read` flag and (if the request is an XMLHttpRequest) return a JSON success response.
- [ ] **GIV-SEC-007**: When a split gift organizer marks an item as purchased, the system shall notify all other contributors. (TODO)
