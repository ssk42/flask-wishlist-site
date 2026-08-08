# Low-Level Design (LLD) - Event Management

## Overview
The Event Management segment handles the lifecycle of gift occasions (Events). It enables authenticated users to create events, associate items with them, and automatically sends reminder emails to users who have claimed items for an upcoming event.

## Core Models

### Event
- **Fields**:
  - `id`: Integer, primary key
  - `name`: String(100), required
  - `date`: Date, required
  - `created_by_id`: Integer (FK to User), required
  - `reminder_sent`: Boolean, default False
  - `created_at`: DateTime, defaults to UTC now
  - `updated_at`: DateTime, defaults to UTC now, updates on change
- **Relationships**:
  - `created_by`: User relationship
  - `items`: Items associated with this event (1-to-many)
- **Constraints/Observations**:
  - `reminder_sent` tracks if the 7-day automated email has been sent.

## Core Workflows

### 1. Event CRUD Operations (`blueprints/events.py`)
- **List Events**:
  - Route: `GET /events`
  - Logic: Displays events grouped into upcoming (>= today) and past (< today) using eager loading for `created_by` and `items` to prevent N+1 queries.
- **Create Event**:
  - Route: `GET|POST /events/new`
  - Form validation: Requires `name` and `date`. [inferred] Date format must be `YYYY-MM-DD`.
  - Logic: Creates an event tied to the current logged-in user.
- **Edit Event**:
  - Route: `GET|POST /events/<int:event_id>/edit`
  - Logic: Allows only the creator of the event (`created_by_id == current_user.id`) to edit it. Updates name and date.
- **Delete Event**:
  - Route: `POST /events/<int:event_id>/delete`
  - Logic: Allows only the creator to delete. Instead of cascading deletes to items, [inferred] the application safely detaches items from the event by setting their `event_id` to `None` prior to deletion.

### 2. Event Reminders (`services/tasks.py`)
- **Task**: `send_event_reminders`
- **Logic**:
  - Identifies events exactly 7 days from today where `reminder_sent` is `False`.
  - Finds all items associated with the event that are either 'Claimed' or 'Purchased' and have a valid `last_updated_by_id` (claimer).
  - Groups the claimed items by the claimer's user ID (filtering out cases where the owner is the claimer).
  - Triggers `send_event_reminder` email for each claimer with a summary of their claimed items.
  - Updates the event's `reminder_sent` flag to `True`.

## Open Questions
- **[inferred] Edge case:** What happens if the reminder script fails halfway through? The event is marked as `reminder_sent = True` only after all claimer emails are attempted, but if the script crashes, duplicate emails might be sent on the next run to some claimers.
- **Quirk:** The event deletion detaches items via a direct update query (`Item.query.filter_by(event_id=event_id).update({'event_id': None})`) instead of using SQLAlchemy cascade rules on the model relationship.
- **Quirk:** The reminder script queries events happening exactly 7 days from today. If the cron job doesn't run on a given day, reminders for that day's events will be permanently skipped (no catch-up mechanism).
