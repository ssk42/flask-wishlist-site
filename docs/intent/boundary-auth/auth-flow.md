# auth-flow LLD

## Core Concept
Handles user authentication and onboarding for the Wishlist application, leveraging a shared secret (Family Code) instead of individual user passwords.

## Data Models
- **User**: Represents a member of the family group.
  - `id`: Primary key
  - `name`: Display name
  - `email`: Contact email

## Components
- **auth blueprint**: Routes for login, registration, and logout.
- **LoginManager**: Flask-Login integration for session management.
- **Limiter**: Rate limits auth endpoints (5 per minute).

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| **[inferred]** Shared Family Code | Individual passwords | Lowers friction for family members while maintaining a private perimeter. |

## Open Questions
- **[inferred]** The auth endpoints are strictly rate limited, but should there be an IP-level ban for repeated failures?
