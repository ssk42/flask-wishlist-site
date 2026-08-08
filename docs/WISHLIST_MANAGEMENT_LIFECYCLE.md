# Wishlist management lifecycle

This document records the release-critical item workflow as it exists in the
application, including the boundaries at which data becomes durable.

## States and transitions

| Action | Preconditions | Persisted transition | Result |
| --- | --- | --- | --- |
| Create | Authenticated user; non-empty description; valid optional values | A new `Item` is committed with the current user as owner | Redirect to the persisted items list with a success message |
| Edit (owner) | Authenticated owner; valid editable values | The existing item's editable fields are committed | Redirect to the persisted items list with a success message |
| Edit (non-owner) | Authenticated non-owner; valid status | `status` and `last_updated_by_id` are committed | Redirect to the persisted items list with a success message |
| Organize | A list filter or sort is submitted | Filter/sort choices are stored in the Flask session; no item is changed | List is re-queried and rendered in the requested order |
| Delete | Authenticated owner; explicit POST confirmation | Item and cascading comments, contributions, and price history are deleted in one commit | Redirect to the persisted items list with a success message |

The item availability state machine is `Available → Claimed → Purchased` (or
back to `Available` through unclaim). `Splitting` is an additional coordinated
gift state. Owners must not see claim/purchase information for their own items.

## Persistence and recovery boundaries

- SQLAlchemy commits are the persistence boundary for creates, edits, and
  deletes. A failed commit must be rolled back and leave the form data intact.
- The items list is always rendered from a fresh query after a successful
  mutation; filter and sort preferences are intentionally kept in the session.
- A form submission token makes create and owner-edit requests idempotent for a
  browser session. Repeating a completed request redirects to the resulting
  list instead of applying the mutation twice.
- Validation failures do not write to the database. The submitted values are
  re-rendered with clear, recoverable error feedback.

## Validation rules

- Description is required and is limited by the database to 750 characters.
- Price, when supplied, must be a non-negative number.
- Quantity, when supplied, must be an integer from 1 through 99.
- Priority and status must be one of the configured choices.
- A selected event must exist; links and image URLs must be HTTP(S) URLs.
- Only the owner can modify item details or delete an item. Non-owners may only
  update status through the existing collaboration flow.

## UI states

- Empty list: the list displays the existing empty-state guidance and Add item
  call to action.
- Saving/deleting: the submitting control is disabled and announces progress.
- Success: the redirected list shows a flash message based on persisted data.
- Recoverable error: validation or persistence failures keep the user on the
  form, preserve their input, and show a message that allows correction/retry.
