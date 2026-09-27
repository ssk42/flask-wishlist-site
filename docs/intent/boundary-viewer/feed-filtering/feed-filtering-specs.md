# Feed Filtering Specs

- [x] **VW-FEED-001**: The system MUST persist the user's active filters (user, status, priority, event, search query, sort options) in their session.
- [x] **VW-FEED-002**: When a user navigates to the items list without URL query parameters, the system MUST restore and apply the filters from their session.
- [x] **VW-FEED-003**: When a user provides new filter values via URL query parameters, the system MUST update the session state with these new values.
- [x] **VW-FEED-004**: The system MUST clear all active filters when the `clear_filters=true` parameter is passed.
- [x] **VW-FEED-005**: The items list MUST filter the displayed items based on the active user, status, priority, event, and text search (case-insensitive substring match on description) filters.
- [x] **VW-FEED-006**: The items list MUST sort the displayed items based on the active `sort_by` and `sort_order` parameters, defaulting to priority ascending.
- [x] **VW-FEED-007**: The system MUST calculate summary totals (count and total price) grouped by user and status.
- [x] **VW-FEED-008**: The system MUST exclude items that belong to the current user and have a status of 'Claimed' or 'Purchased' from the summary totals to prevent revealing surprises.

- [x] **VW-FEED-009**: When loading the web items list, the system shall eagerly load scalar owners and last updaters and fetch comments with authors and contributions with contributors in separate select-in batches, without joining both collections into the main item query or issuing a relationship query per item.
- [x] **VW-FEED-010**: When applying eager loading to the web items list, the system shall preserve item membership, ordering, grouping, filters, summary values, and owner visibility, including items with empty collections and ORM identifier sets requiring multiple batches.
- [x] **VW-FEED-011**: When exporting all active items, the system shall eagerly load item owners in the item query while preserving export columns, values, and archived-item exclusion.
- [x] **VW-FEED-012**: When constructing model timestamp declarations through a shared helper, the system shall create independent columns with callable UTC defaults and applicable update callbacks evaluated at write time, preserving each column's existing type, nullability, and index options.
- [x] **VW-FEED-013**: When loading the core ORM models, the system shall preserve table names, column types and nullability, defaults, indexes, constraints, relationship names and cascades, and existing import paths.
- [x] **VW-FEED-014**: When evaluating Item split properties after ORM cleanup, the system shall preserve their existing results, including zero progress for absent or zero prices; when flushing a changed item link, the system shall preserve the price-backoff reset behavior defined by AUTO-PRC-014.
