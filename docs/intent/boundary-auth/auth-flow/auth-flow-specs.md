# auth-flow EARS Specifications

- `[x]` **AUTH-FLOW-001**: While registering, the system requires the correct `FAMILY_PASSWORD` to successfully create a new user account.
- `[x]` **AUTH-FLOW-002**: While logging in, the system requires the correct `FAMILY_PASSWORD` matching the global config.
- `[x]` **AUTH-FLOW-003**: If a user attempts to log in with an incorrect email, the system rejects the login attempt.
- `[x]` **AUTH-FLOW-004**: If a user attempts to log in or register more than 5 times per minute, the system returns a 429 Too Many Requests response.
- `[x]` **AUTH-FLOW-005**: While unauthenticated, if a user requests a protected page, the system redirects them to the login page and preserves the original requested URL as a `next` parameter.
- `[x]` **AUTH-FLOW-006**: After a successful login, if a `next` parameter exists and is a safe internal URL, the system redirects the user to that URL.
