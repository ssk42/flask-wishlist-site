# ui-state EARS Specifications

- [x] **VW-UI-001**: While viewing a list, if a user submits a request containing new filter parameters, the system shall save those filter parameters to the user's session.
- [x] **VW-UI-002**: When checking a request for new filter parameters, if the request provides only empty parameter values (e.g., `?status_filter=`), the system shall not overwrite the existing saved session filters.
- [x] **VW-UI-003**: If a request to the filtered list includes the parameter `clear_filters=true`, the system shall purge all saved filter parameters from the user's session.
- [x] **VW-UI-004**: When returning a user to a list view after an action (e.g., editing an item), the system shall automatically append the current active filters from the session to the redirect URL.
- [x] **VW-UI-005**: When an application process requires sending user feedback prior to a redirect, the system shall enqueue the flash message and execute the redirect via a combined view helper to reduce duplication.
