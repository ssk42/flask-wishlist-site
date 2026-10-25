# auth-flow EARS Specifications

- `[x]` **AUTH-FLOW-001**: While registering, the system creates a new user account from a name and email address only — no family code or password is required (changed 2026-10-25: family-code web auth removed to keep sign-in simple; the family code still gates the iOS API login).
- `[x]` **AUTH-FLOW-002**: While logging in, the system requires only the user's name, matched case-insensitively against the unique account name — no email, password, or family code.
- `[x]` **AUTH-FLOW-003**: If a user attempts to log in with a name that matches no account, the system rejects the login attempt.
- `[x]` **AUTH-FLOW-004**: If a user attempts to log in or register more than 5 times per minute, the system returns a 429 Too Many Requests response.
- `[x]` **AUTH-FLOW-005**: While unauthenticated, if a user requests a protected page, the system redirects them to the login page and preserves the original requested URL as a `next` parameter.
- `[x]` **AUTH-FLOW-006**: After a successful login, if a `next` parameter exists and is a safe internal URL, the system redirects the user to that URL.
