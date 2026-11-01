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

## Browser Delivery of HTMX Actions

Claim and unclaim controls are HTMX actions rendered by the base template on
every page. For those controls to work, the browser must actually load the
HTMX library and attach the session's CSRF token to each HTMX request. The
production Content-Security-Policy permits scripts only from the application's
own origin and jsDelivr, with no inline script. The base template therefore
loads HTMX from jsDelivr (the same origin already used for Bootstrap) with a
pinned subresource-integrity hash, and an external static script reads the
CSRF token from a `csrf-token` meta element in the page head and registers the
`htmx:configRequest` listener that sets the `X-CSRFToken` header. No part of
this wiring relies on inline script or on a script origin the policy does not
allow.

The CSP exists only in `ProductionConfig`; the testing configuration serves
no policy and the Flask test client does not enforce one, so divergence
between the template's script origins and the production policy is invisible
to ordinary request/response tests. The regression tests for this contract
therefore read the production policy directly and check every external
script origin the base template renders against its script-src allowlist.

## Card Geometry Stability

Claim and unclaim are HTMX swaps: the server returns a freshly rendered
card and the browser replaces the old card in place. For that swap to leave
the surrounding grid undisturbed, the card's rendered height must not depend
on its claim state. Two parts of the full item card (`partials/_item_card.html`)
previously varied with status: the "Claimed by" attribution line existed
only while an item was Claimed, and the claimed-by-the-viewer action block
stacked its two controls vertically while the available state used a single
row of pills, roughly doubling the action area's height.

The card therefore reserves both slots in every state. The attribution line
renders for every viewer who does not own the item — populated while the
item is Claimed, empty otherwise — as a single line that never wraps. The
action area is one row in every state (available, splitting, claimed by the
viewer, claimed by another user, and the owner's own controls) and carries
a minimum height (`item-card-actions`) equal to the tallest single-row
variant, so the row's height is constant. The price and "as of" date line
never wraps, so its height is constant at any column width. Together these
keep a card's height identical before and after a claim or unclaim swap.
This is specified by GIV-CLM-020.

The dashboard card (`partials/_dashboard_item_card.html`) does not need the
same treatment: every one of its states renders a single row of same-height
pill or badge elements and it has no attribution line, so its swaps already
preserve height. The split-progress block shown while an item is Splitting
is content, not part of the action area; entering or leaving Splitting
happens through the split flow, not through a claim swap.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| Request-local grouped claim summary | Separate counts for each consumer; cross-request count cache | One aggregate serves both statuses without adding stale data or cache invalidation across requests. Complete My Claims results can supply the same values. |
| **[inferred]** Using `last_updated_by_id` to track the claimer instead of a dedicated `claimed_by_id` field. | Creating a specific `claimed_by_id` foreign key. | Reusing the audit field simplifies the schema, though it couples audit history with business logic (claiming). |
| **[inferred]** Returning HTMX partials for claim/unclaim when requested via `HX-Request`. | Always redirecting back to the previous page. | HTMX provides a smoother, SPA-like user experience without full page reloads. |
| **[inferred]** Hiding claims from the item owner ("surprise protection"). | Showing all claims to everyone. | Essential for a wishlist application so the recipient's gift is not ruined. |
| Loading HTMX from jsDelivr and wiring the CSRF header from an external static script that reads a `csrf-token` meta element. | Adding unpkg to the CSP script-src; keeping the inline configRequest listener with a CSP nonce; self-hosting the HTMX file under `/static`. | The production policy deliberately allows only the app origin and jsDelivr; aligning the template to the policy keeps one trusted CDN (already used for Bootstrap) and avoids widening the policy or adding nonce plumbing. Self-hosting remains a valid future option but changes the asset pipeline for one library. |
| Geometry-neutral claim swaps: reserve the attribution line in all non-owner states, keep the action area to a single row in every state, and floor the action area's height at the tallest single-row variant. | Leave the claimed state's stacked action block and status-only attribution line in place; or fix the whole card to one constant height. | The stacked block and conditional line change card height on every claim/unclaim swap and reflow the grid the user is looking at. A fixed whole-card height fights the grid's row equalization (`h-100`) and wastes vertical space on short cards. Reserving the two state-dependent slots keeps every state's footprint identical with no visual redesign. |

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
