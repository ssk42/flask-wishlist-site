# system-tasks EARS Specifications

- [x] **AUTO-TSK-001**: **While** executing the event reminders task, the system shall identify all events occurring exactly 7 days in the future where `reminder_sent` is false.
- [x] **AUTO-TSK-002**: **For each** matching event, the system shall gather all associated items that have a status of 'Claimed' or 'Purchased' and possess a known claimer (`last_updated_by_id`).
- [x] **AUTO-TSK-003**: **If** an event has no claimed items, the system shall mark the event's `reminder_sent` attribute to true and proceed to the next event.
- [x] **AUTO-TSK-004**: **For each** user who has claimed items for a given event, the system shall dispatch a single reminder email consolidating all of their claimed items for that event.
- [x] **AUTO-TSK-005**: **If** a reminder email fails to send or encounters an exception, the system shall log the error, increment the error count, and continue processing remaining users and events.
- [x] **AUTO-TSK-006**: **After** processing all claimed items for an event (or encountering no claimed items), the system shall mark the event's `reminder_sent` attribute to true.
- [x] **AUTO-TSK-007**: **If** a Celery asynchronous task (`send_event_reminders_async` or `update_stale_prices_async`) raises an unhandled exception, the system shall log the failure and retry the task up to 3 times with a 60-second countdown.
- [x] **AUTO-TSK-008**: **When** the Celery application initializes, if the Redis broker URL uses the `rediss://` protocol, the system shall append `?ssl_cert_reqs=none` to the URL.
- [x] **AUTO-TSK-009**: **When** an asynchronous task runs, it shall initialize a new Flask application context before executing the underlying synchronous core logic.
- [x] **AUTO-TSK-010**: **When** the Celery Beat scheduler runs, the system shall dispatch the `update_stale_prices_async` task every 6 hours so items past the 7-day staleness window are refreshed within 6 hours.
- [x] **AUTO-TSK-011**: **While** the `update_stale_prices_async` task executes a catch-up batch (all items stale), the task shall run under a 40-minute time limit rather than the worker's 300-second default, so large post-gap batches complete instead of being killed.
