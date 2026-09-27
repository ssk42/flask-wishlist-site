# item-claiming LLD

## Core Concept
The item-claiming segment allows users (gift givers) to claim items from other users' wishlists to avoid duplicate gifts. It implements "surprise protection," ensuring that item owners cannot see who has claimed or purchased their own items. The segment also provides a "My Claims" view where users can track the items they've claimed or purchased for others, organized by recipient.

## Data Models
- **Item**:
  - `status`: String representing the state of the item (e.g., 'Available', 'Claimed', 'Purchased').
  - `user_id`: The ID of the user who owns the item.
  - `last_updated_by_id`: The ID of the user who most recently updated the item, which effectively acts as the "claimer" ID when an item's status transitions to 'Claimed'.
- **User**:
  - Contains information about the claimer or the item owner.

## Components
- **Claim Action (`claim_item`)**: Endpoint that allows a user to mark an 'Available' item as 'Claimed'. It updates `status` and `last_updated_by_id`.
- **Unclaim Action (`unclaim_item`)**: Endpoint that allows the user who claimed an item to revert its status back to 'Available'.
- **My Claims Page (`my_claims`)**: A dashboard for gift givers showing all items they have claimed or purchased. Groups the items by the item owner (recipient).
- **Navbar Badge**: Displays the count of currently claimed (but not yet purchased) items for the logged-in user.
- **Dashboard Widget**: Displays claimed and purchased counts when the user has active claims.

## Claim Summary Queries

The navbar, dashboard, and My Claims use the same claim population: items with
`last_updated_by_id` equal to the viewer, `user_id` different from the viewer,
and `archived_at` null. Only `Claimed` and `Purchased` contribute to the respective
counts. Missing groups yield integer zero; split contributions remain separate.

A shared query helper returns both counts with one grouped aggregate. Its result
is reused for that viewer within the request. My Claims seeds the same request
summary from its complete, unpaginated item collection, avoiding another count
query. Filtered item lists must not seed this summary because the badge describes
all of the viewer's active claims. Request reuse is keyed by viewer ID and is
populated after route mutations; if a caller mutates claims after reading the
summary, it must invalidate that request entry before rendering again.

The dashboard's existing per-user 60-second response cache retains its existing
lifetime. On a cache miss, its widget and navbar consume the same summary. The
request summary itself is never saved in cookies or a cross-request cache.

My Claims loads collection relationships in batches and scalar owners/authors
alongside their parent rows. Collection loading preserves recipient grouping,
item ordering, and the separate split-contribution list.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| Request-local grouped claim summary | Separate counts for each consumer; cross-request count cache | One aggregate serves both statuses without adding stale data or cache invalidation across requests. Complete My Claims results can supply the same values. |
| **[inferred]** Using `last_updated_by_id` to track the claimer instead of a dedicated `claimed_by_id` field. | Creating a specific `claimed_by_id` foreign key. | Reusing the audit field simplifies the schema, though it couples audit history with business logic (claiming). |
| **[inferred]** Returning HTMX partials for claim/unclaim when requested via `HX-Request`. | Always redirecting back to the previous page. | HTMX provides a smoother, SPA-like user experience without full page reloads. |
| **[inferred]** Hiding claims from the item owner ("surprise protection"). | Showing all claims to everyone. | Essential for a wishlist application so the recipient's gift is not ruined. |

## Open Questions
- **[inferred]** Bug/Quirk: If another user edits an item (e.g., changes price) while it's claimed, `last_updated_by_id` might be overwritten, potentially re-assigning or losing the "claimer" record? The codebase seems to rely heavily on `last_updated_by_id` for ownership of the claim.
- **[inferred]** TODO marker about sending notifications to other contributors. Are notifications fully integrated into the claim workflow?

## Request Summary Consistency

Changes to status, archive state, deletion, owner, or last updater after a summary
read invalidate affected viewer summaries before reuse. Complete My Claims
results seed both counts, including zeros for an empty collection, after pending
ORM writes are flushed. Seeding replaces earlier request values.

## ORM Requirement Traceability

Claim-summary behavior is specified by GIV-CLM-009 and GIV-CLM-012 through GIV-CLM-017 in [the item-claiming requirements](item-claiming/item-claiming-specs.md).

Completed split items count once as Purchased for their organizer when they meet
the summary predicate; contribution rows never add counts. Rollback and bulk
writes affecting the summary invalidate request reuse, including old and new
viewers after reassignment. HTMX card responses retain their existing scope;
sidebar badges update on a later full render under its response cache policy.
