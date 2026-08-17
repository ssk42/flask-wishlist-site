---
status: AUDITED
---

# auth-flow Arrow

This segment encompasses the public authentication perimeter: family code validation, registration, login sessions, and rate limiting.

## Artifacts
- **LLD**: [docs/intent/boundary-auth/auth-flow.md](../../intent/boundary-auth/auth-flow.md)
- **EARS Specs**: [docs/intent/boundary-auth/auth-flow/auth-flow-specs.md](../../intent/boundary-auth/auth-flow/auth-flow-specs.md)
- **Tests**:
  - `tests/unit/test_family_auth.py`
  - `tests/unit/test_rate_limiting.py`
  - `tests/unit/test_routes.py`
  - `tests/unit/test_forgot_email.py`
  - `tests/browser/test_login_logout_flow.py`
- **Code**:
  - `blueprints/auth.py`
  - `app.py` (login_view config, request_loader)
  - `templates/login.html`
  - `templates/registration.html`
