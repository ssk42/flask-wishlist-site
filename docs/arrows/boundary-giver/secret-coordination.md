---
status: AUDITED
---

# secret-coordination Arrow

## Artifacts
- **LLD**: [docs/intent/boundary-giver/secret-coordination.md](../../intent/boundary-giver/secret-coordination.md)
- **EARS Specs**: [docs/intent/boundary-giver/secret-coordination/secret-coordination-specs.md](../../intent/boundary-giver/secret-coordination/secret-coordination-specs.md)
- **Tests**: `tests/unit/test_comments.py`, `tests/unit/test_split_gifts.py`,
  `tests/unit/test_surprise_protection.py`
- **Code**: `blueprints/social.py`, `blueprints/items.py` (complete_split, summary
  totals), `services/notification_service.py`

## Key Findings

1. **GIV-SEC-007 implemented 2026-08-16** — `complete_split` now notifies every
   other contributor (excluding organizer + item owner) via `create_notification`,
   mirroring the comment-notification pattern. The split-completion TODO is gone.
2. **Ordering is tested** — `/notifications` renders newest-first (GIV-SEC-005),
   verified with explicit timestamps.
