# ui-state LLD

## Core Concept
The UI State segment manages the persistence of view state and presentation layer logic for the application's viewers (end users). Specifically, it ensures that transient view states (such as active search filters, sorts, and selected scopes) remain intact as a user navigates between list views and item detail/edit pages, ensuring a seamless browsing experience. It also encapsulates boilerplate UI orchestration routines such as flashing feedback messages prior to redirects.

## Data Models
There are no dedicated database models for this segment. Persistent filter state is maintained within the `Flask session` (a client-side signed cookie — not server-held, though the signature makes it tamper-evident).
Navigation summaries exist only on the current request object.
The `SessionFilterManager` manages the following keys in the session:
- `user_filter`: ID of the user whose items are being viewed
- `status_filter`: The claim/purchase status filter
- `priority_filter`: The urgency/priority filter
- `event_filter`: ID of the event being filtered
- `q`: Search query string
- `sort_by`: Column used for sorting (defaults to `priority`)
- `sort_order`: Direction of sort (`asc` or `desc`, defaults to `asc`)

## Components

### `SessionFilterManager`
A utility class that encapsulates filter state.
- **`__init__(request_obj)`**: Binds to the current Flask request.
- **`get_filters()`**: Central method that resolves the active state. If the current request contains new, valid filter parameters, it saves them to the session. Otherwise, it loads the prior filters from the session.
- **`has_new_filters()`**: Evaluates whether the request contains new truthy filter values. Empty query parameters do not count.
- **`save_from_request()`**: Mutates the session dictionary with the parsed request arguments.
- **`clear_all()`**: Purges all tracked filter keys from the session.
- **`should_clear()`**: Checks if `clear_filters=true` is present in the query string.

### View Helpers (`services/utils.py` & `services/view_helpers.py`)
- **`get_items_url_with_filters()`**: Rebuilds the URL to `items.items_list` and automatically attaches any active session filters as query parameters. This is used by redirect flows to return users exactly to where they left off.
- **`flash_and_redirect(message, category, endpoint, **kwargs)`**: A DRY helper for the common Web UI pattern: enqueue a flash message in the session and immediately redirect the user.

## Navigation Database Access

Context processors expose callable badge helpers without evaluating database
counts. The authenticated sidebar invokes each helper once and stores its result
in a template-local variable. A template that does not render the sidebar causes
no navigation count queries, including HTMX cards and modal fragments. Anonymous
renders return zero without querying either badge population.

Claim counts come from the item-claiming summary helper. Unread counts use the
existing notification rule, `user_id` equal to the viewer and `is_read` false.
Each computed value is reused only within the current request and viewer. A
complete notification list can seed its unread count after loading, while a
filtered or paginated collection cannot. Callers that mutate notifications after
reading the count invalidate that request entry before rendering again.

A fresh full page that needs a badge still queries when the request has no
reusable result. Navigation freshness follows the surrounding response's cache
policy; no additional cross-request badge cache is introduced.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| Lazy sidebar badge helpers | Eager context-processor queries; endpoint allowlists | The template determines whether badges are needed, including when the same endpoint serves full pages and fragments. |
| **[inferred]** Store UI filters in Flask Session (server-side tracking) | Store filters purely in the URL or use frontend-only state (e.g., localStorage/React context). | Flask session enables traditional full-page navigation while preserving state across disjoint actions (like an edit modal or separate page), without requiring heavy JS architecture. |
| **[inferred]** Ignore empty filter params when updating session | Overwrite session blindly based on request keys. | If a user navigates to the bare `/items` URL without parameters, their previous session state should persist rather than being wiped out. |
| **[inferred]** Require explicit `clear_filters=true` to reset state | Resetting on any navigation to the base `/items` path. | Users often click "Gifts" in the nav bar expecting their filters to clear, but here a specific clear action is required, ensuring they don't accidentally lose a complex filter setup. |

## Open Questions
- **[inferred]** The `get_items_url_with_filters` currently hardcodes the exact same keys that `SessionFilterManager` manages. Could this be refactored so `SessionFilterManager` handles URL generation or exposes its `FILTER_KEYS` constant?
- **[inferred]** Is the session cookie growing too large if a user opens multiple tabs with different filter contexts? Flask sessions are global to the browser, so filtering in one tab will leak into another tab.

## Unread Summary Consistency

Changes to read state, notification creation/deletion, or recipient after a count
read invalidate affected viewer counts before reuse. A complete notification list
seeds its unread count after pending ORM writes are flushed, including zero for
an empty list. Seeding replaces earlier request values.

## ORM Requirement Traceability

Navigation query behavior is specified by VW-UI-006 through VW-UI-011 in [the UI-state requirements](ui-state/ui-state-specs.md).

Rollback and bulk notification writes invalidate request unread counts before
reuse. Recipient reassignment invalidates both old and new viewer entries.
