---
status: OK
---

# item-curation Arrow

## Artifacts
- **LLD**: [docs/intent/boundary-owner/item-curation.md](../../intent/boundary-owner/item-curation.md)
- **EARS Specs**: [docs/intent/boundary-owner/item-curation/item-curation-specs.md](../../intent/boundary-owner/item-curation/item-curation-specs.md)

## Key Findings

1. **Archive shipped 2026-09-03** — `OWN-ITEM-009`–`017` implemented, 11 tests green, migration `c7d9e1f2a3b4` applied on hp-server. Exclusion enforced on reads (list, dashboard, totals, My Claims, event pickers, v1 list/detail) and actions (web guards + v1 getter 404).
2. **014 vs v1 tension** — web lets owners edit archived items (stays archived, `014`); v1 `PATCH` 404s them via the archived-nulling getter. Conscious divergence, not a bug, but the pair should be reconciled if native archive UI ever lands.

## Work Required

1. ~~Archived items still leak into secondary surfaces~~ Resolved 2026-09-03 — `export_my_status_updates`, `/users` counts, and event-reminder claimed items now filter `archived_at` (`OWN-ITEM-012`), covered by `TestArchivedSecondarySurfaces`.
