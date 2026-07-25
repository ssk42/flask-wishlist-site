# system-tasks LLD

## Core Concept
The system-tasks segment is responsible for managing and executing autonomous background processes. Its primary goal is to decouple long-running or periodic jobs (such as sending event reminders or updating stale item prices) from the web request cycle. This ensures the application can proactively notify users and keep data fresh without relying solely on direct user interactions, leveraging Celery and Redis for reliable asynchronous task execution.

## Data Models
The tasks operate over existing domain models without owning specific tables:
- **Event**: Read to find upcoming dates (`date`) and mutated to prevent duplicate emails (`reminder_sent`).
- **Item**: Filtered by `event_id`, `status` (Claimed/Purchased), and `last_updated_by_id` to identify which users claimed gifts for an event.
- **User**: Queried to retrieve contact information (name, email) for reminder recipients.
- **Notification**: Referenced as a dependency for price update side effects.

## Components
- **`services/tasks.py`**: Contains the synchronous core business logic for tasks. For example, `send_event_reminders` computes the date offset, groups claimed items by user, triggers email sending, and updates event state.
- **`services/celery_tasks.py`**: Defines the Celery `@celery_app.task` wrappers (`send_event_reminders_async`, `update_stale_prices_async`). These wrappers create a fresh Flask application context and handle exceptions and retries.
- **`celery_app.py`**: Configures the Celery application, managing the Redis broker connection (including Heroku SSL quirks) and defining worker constraints like timeouts and serializers.
- **`tests/unit/test_tasks.py`**: Validates the synchronous task logic with mocked external dependencies (like `email_service`), ensuring robust testability without needing a live Celery worker.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| **[inferred]** Decoupled synchronous core logic from Celery decorators. | Putting business logic directly inside `@celery_app.task` functions. | Allows `test_tasks.py` to test task logic natively with the standard Flask test client/app context, avoiding the complexity of spinning up or mocking a Celery worker. |
| **[inferred]** Event idempotency via `reminder_sent` boolean. | Tracking sent emails per user or just relying on a strict once-a-day cron trigger. | Storing state on the `Event` guarantees that even if the background task runs multiple times on the 7-day mark, reminders won't be spammed. |
| **[inferred]** Retry mechanism on Celery tasks (`max_retries=3, countdown=60`). | Letting tasks fail silently or immediately retrying. | Network calls (emails, price scraping) are inherently flaky; an exponential or delayed retry increases reliability. |
| **[inferred]** Hardcoded 7-day event reminder offset. | User-configurable reminder dates. | Simplifies the initial implementation while covering the most common use case for gift buying. |

## Open Questions
- **[inferred]** If an event has zero claimed items exactly 7 days prior, the task marks `reminder_sent = True`. If a user subsequently claims an item *after* this run (e.g., 5 days before), they will never receive a reminder. Is this intended behavior or an edge case bug?
- **[inferred]** How are these periodic tasks scheduled? (e.g., Celery Beat schedule configuration is not present in this immediate segment).
- **[inferred]** Is there a requirement to notify the event creator if *no* items have been claimed as the event approaches?
