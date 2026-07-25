# Feed Filtering Specs

- [x] **VW-FEED-001**: The system MUST persist the user's active filters (user, status, priority, event, search query, sort options) in their session.
- [x] **VW-FEED-002**: When a user navigates to the items list without URL query parameters, the system MUST restore and apply the filters from their session.
- [x] **VW-FEED-003**: When a user provides new filter values via URL query parameters, the system MUST update the session state with these new values.
- [x] **VW-FEED-004**: The system MUST clear all active filters when the `clear_filters=true` parameter is passed.
- [x] **VW-FEED-005**: The items list MUST filter the displayed items based on the active user, status, priority, event, and text search (case-insensitive substring match on description) filters.
- [x] **VW-FEED-006**: The items list MUST sort the displayed items based on the active `sort_by` and `sort_order` parameters, defaulting to priority ascending.
- [x] **VW-FEED-007**: The system MUST calculate summary totals (count and total price) grouped by user and status.
- [x] **VW-FEED-008**: The system MUST exclude items that belong to the current user and have a status of 'Claimed' or 'Purchased' from the summary totals to prevent revealing surprises.
