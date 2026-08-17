# ui-state LLD

## Core Concept
The UI State segment manages the persistence of view state and presentation layer logic for the application's viewers (end users). Specifically, it ensures that transient view states (such as active search filters, sorts, and selected scopes) remain intact as a user navigates between list views and item detail/edit pages, ensuring a seamless browsing experience. It also encapsulates boilerplate UI orchestration routines such as flashing feedback messages prior to redirects.

## Data Models
There are no dedicated database models for this segment. All state is maintained within the `Flask session` (a client-side signed cookie — not server-held, though the signature makes it tamper-evident). 
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

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| **[inferred]** Store UI filters in Flask Session (server-side tracking) | Store filters purely in the URL or use frontend-only state (e.g., localStorage/React context). | Flask session enables traditional full-page navigation while preserving state across disjoint actions (like an edit modal or separate page), without requiring heavy JS architecture. |
| **[inferred]** Ignore empty filter params when updating session | Overwrite session blindly based on request keys. | If a user navigates to the bare `/items` URL without parameters, their previous session state should persist rather than being wiped out. |
| **[inferred]** Require explicit `clear_filters=true` to reset state | Resetting on any navigation to the base `/items` path. | Users often click "Gifts" in the nav bar expecting their filters to clear, but here a specific clear action is required, ensuring they don't accidentally lose a complex filter setup. |

## Open Questions
- **[inferred]** The `get_items_url_with_filters` currently hardcodes the exact same keys that `SessionFilterManager` manages. Could this be refactored so `SessionFilterManager` handles URL generation or exposes its `FILTER_KEYS` constant?
- **[inferred]** Is the session cookie growing too large if a user opens multiple tabs with different filter contexts? Flask sessions are global to the browser, so filtering in one tab will leak into another tab.
