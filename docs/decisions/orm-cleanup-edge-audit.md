# ORM Cleanup: Cross-Component Edge Audit

Status: approved.

## Decisions

| Interaction | Ambiguity | Resolution |
|---|---|---|
| GIV-CLM-012 and GIV-SPL-006 | “Excluding split contributions” could exclude a completed split item even though completion assigns Purchased status and the organizer as last updater. | Count qualifying Item rows once. A completed split counts as a purchased item for its organizer. Contribution rows never add counts; active Splitting items do not enter either status count. |
| GIV-CLM-015, VW-UI-011, and transaction lifecycle | A summary computed after a flush can survive a subsequent rollback in request memory. Bulk notification updates may bypass per-object change tracking. | Invalidate request summaries on rollback and ensure bulk writes affecting their populations invalidate before reuse. Read again from current state; invalidate both previous and new viewers for reassignment. |
| GIV-CLM-010 and VW-UI-006 | Removing navigation queries from HTMX responses might be interpreted as also adding live badge updates. | Preserve the existing item-card-only response. The displayed sidebar updates on a subsequent full render, subject to the existing dashboard response cache. |

## Consistency Findings

- Archive exclusion in GIV-CLM-009/012 agrees with OWN-ITEM-012. Restoring an item makes its preserved claim eligible again.
- Request summaries must not be seeded from a filtered feed: global badges and visible feed totals have different populations.
- Request-local query reuse does not bypass the dashboard response cache. Cached HTML can retain its existing 60-second lifetime.
- Eager loading does not authorize rendering owner-hidden comments, contributors, claim status, or last-updater identity. OWN-VIS-001 through OWN-VIS-006 remain authoritative for presentation.
- Collection batches must preserve parent ordering; SQL statement count may grow by identifier batches rather than by individual items.
- Timestamp cleanup preserves existing database types and callable defaults; it does not change timezone storage semantics or require a schema migration.

## Validation Implications

Tests should distinguish claim-summary queries from ordinary item queries, and navigation queries from route-required notification queries. Test cache misses explicitly when counting dashboard SQL. Cover empty lists, multiple viewers, archive/restore, completed splits, rollback, bulk notification updates, and owner-hidden content alongside relationship loading and schema compatibility.

Behavior-preserving model checks are characterization tests and should pass before and after the cleanup. New query-budget and archive-badge regression tests should fail for their intended reasons before implementation; forcing compatibility checks to fail would contradict the preservation requirements.

## References

- [Claim design](../intent/boundary-giver/item-claiming.md)
- [Navigation design](../intent/boundary-viewer/ui-state.md)
- [Loading and model design](../intent/boundary-viewer/feed-filtering.md)
