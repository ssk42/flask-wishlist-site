# feed-filtering LLD

## Core Concept
The feed-filtering system provides a persistent, session-backed mechanism for gift givers (viewers) to find, sort, and organize wishlist items across the platform. By persisting filters in the session via `SessionFilterManager`, users can navigate away to view an item or claim it, and return to their exact filtered view. It also ensures "surprise protection" by omitting the current user's claimed/purchased gifts from summary statistics.

## Data Models
- **[inferred]** `SessionFilterManager`: Extracts and maintains filter state (`user_filter`, `status_filter`, `priority_filter`, `event_filter`, `q`, `sort_by`, `sort_order`) in the Flask session.
- **[inferred]** Filters are applied to the `Item` model, which joins with `User`, `last_updated_by`, `Comment`, and `Contribution`.

## Components
- **Filter UI (`items_list.html`)**: A sidebar or top-bar containing dropdowns for User, Status, Priority, Event, and Sort, plus a text search input.
- **Filter Persistence (`SessionFilterManager`)**: Parses request arguments. If present, it updates the session state. If absent, it restores the session state. It provides a `should_clear()` method to reset the session.
- **Query Builder (`items_list` route)**: Applies SQL alchemy filters dynamically based on the active `SessionFilterManager` state.
- **Surprise Protection (`items_list` route)**: A grouping logic step that prevents the current user's claimed/purchased items from being tallied in the summary totals, avoiding revealing surprises.

## ORM Loading and Model Compatibility

The items list uses scalar eager loading for the owner and last updater, and
separate select-in batches for comments and contributions. Each comment batch
loads authors; each contribution batch loads contributors. Loading two independent
collections must not produce a comments-by-contributions product in the main item
query. The explicit owner join needed for sorting remains available.

Loader choices preserve item membership, ordering, grouping, filters, and summary
values. Empty collections remain valid. Batch queries may increase in steps for
large lists as the ORM divides identifiers into batches; they must not issue a
relationship query for every item. Owner visibility remains enforced by existing
presentation and summary rules.

The all-items export eagerly loads each item's owner in its item query. Its
active-item scope, columns, and values remain unchanged.

Core model cleanup preserves table names, column types, nullability, defaults,
indexes, constraints, relationship names, cascade behavior, and import paths.
Timestamp declaration helpers create a fresh Column per declaration and retain
callable UTC defaults and update callbacks; timestamps are evaluated at write
time, not import time. Indexed timestamp columns keep their existing indexes.
Model formatting and redundant split-progress condition cleanup preserve public
property values, including zero or absent prices. The price-backoff flush listener
retains its existing link-change behavior. These mechanical conventions support
all consumers without moving their business rules into this segment.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| Select-in collection loading and joined scalar loading | Join every collection; lazy-load every relationship | Separate collection batches avoid multiplying result rows and per-item queries while preserving scalar access. |
| Fresh timestamp column factory with callable UTC defaults | Timestamp inheritance mixins; import-time timestamp values | A factory preserves explicit model declarations and column options without introducing inheritance or freezing timestamps. |
| **[inferred]** Persist filters in server-side Flask session. | Use client-side URL parameters only (e.g., passing `?status=...` everywhere). | Session persistence simplifies URL generation in other parts of the app (like HTMX redirects or return links) without having to drill URL params through every template. |
| **[inferred]** Soft-ignore empty filter params in `has_new_filters()`. | Overwrite session with empty params if the form submits empty fields. | Allows navigating back to `/items` without accidental filter wipes if some params are dropped, while still letting explicit clears work via `?clear_filters=true`. |
| **[inferred]** Implement surprise protection in Python memory (during `totals_dict` generation). | Implement surprise protection purely in the database query. | Filtering in memory allows fetching the required items with batched relationships, grouping them, and then conditionally tallying them based on the current user's context without complex SQL conditionals. |

## Open Questions
- **[inferred]** What happens if a user opens multiple tabs with different filter contexts? Since filters are tied to the Flask session, changing filters in one tab will silently change the filter context for the other tab on next load.
- **[inferred]** Should we limit the length of the search query (`q`) in the session to prevent session cookie bloat?

## ORM Requirement Traceability

Loading and core model compatibility are specified by VW-FEED-009 through VW-FEED-014 in [the feed requirements](feed-filtering/feed-filtering-specs.md).
