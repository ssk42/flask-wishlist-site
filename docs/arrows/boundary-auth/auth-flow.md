---
status: MAPPED
---

# auth-flow Arrow

This segment encompasses the public authentication perimeter: family code validation, registration, login sessions, and rate limiting.

## Artifacts
- **LLD**: [docs/intent/boundary-auth/auth-flow.md](../../intent/boundary-auth/auth-flow.md)
- **EARS Specs**: [docs/intent/boundary-auth/auth-flow/auth-flow-specs.md](../../intent/boundary-auth/auth-flow/auth-flow-specs.md)
- **Tests**:
  - `tests/unit/test_family_auth.py`
  - `tests/unit/test_rate_limiting.py`
- **Code**:
  - `blueprints/auth.py`
  - `templates/login.html`
  - `templates/registration.html`
