# Account Recovery (Forgot Email) Low-Level Design

## Purpose
Provides a mechanism for users to recover their email address by searching for their registered name. Since the application uses a shared "Family Code" instead of individual passwords, users only need their email and the shared code to log in. Thus, the only account recovery necessary is recovering a forgotten email address.

## Scope
- User submits their name via a form.
- The system searches for the name in the database.
- If a match is found, the user's email is revealed to them.
- If multiple matches are found, the system advises the user to contact support.
- If no match is found, the system displays an error.

## Key Components

### Routes (`blueprints/auth.py`)
- `GET /forgot_email`: Renders the account recovery page.
- `POST /forgot_email`: Processes the form submission.
  - Receives `name` from `request.form`.
  - Strips whitespace.
  - Returns a warning flash if `name` is empty.
  - Performs a case-insensitive search (`ilike`) in the `User` model for the provided name.
  - **Match handling:**
    - `len(users) == 1`: Exact match. Renders the template with `found_email` and `found_name`.
    - `len(users) > 1`: Multiple matches. Flashes a warning telling the user to contact support.
    - `len(users) == 0`: No match. Flashes a danger message telling the user to check spelling or sign up.
  - [inferred] Limits requests to 5 per minute via `@limiter.limit("5 per minute")` to prevent abuse/enumeration.

### Templates (`templates/forgot_email.html`)
- Extends `base.html`.
- Two main states:
  - **Search State:** A form to input `name`. Contains a "Find My Email" submit button and a link back to login.
  - **Found State:** Displays the user's email address in a copyable block. Includes a direct login form that is pre-filled with the found email address and submits to the login route, so the user can just click "Log in as {name}".
- [inferred] Uses Bootstrap classes for styling (`alert-success`, `d-grid`, `btn-primary`, etc.).

### Tests
- **Unit Tests** (`tests/unit/test_forgot_email.py`):
  - `test_forgot_email_page_loads`: Checks successful page render.
  - `test_forgot_email_finds_exact_match`: Verifies correct search behavior for exact match.
  - `test_forgot_email_case_insensitive`: Verifies case-insensitive search.
  - `test_forgot_email_not_found`: Checks behavior on non-existent user.
  - `test_forgot_email_empty_name`: Validates empty input handling.
  - `test_forgot_email_strips_whitespace`: Verifies that leading/trailing whitespaces are stripped.
  - `test_login_page_has_forgot_email_link`: Ensures entry point from login exists.
- **Browser Tests** (`tests/browser/test_login_logout_flow.py`):
  - `test_forgot_email_page_renders`: Verifies visual rendering.
  - `test_forgot_email_with_valid_name`: Tests full end-to-end flow with a registered user name.
  - `test_forgot_email_with_invalid_name`: Tests end-to-end flow for failure.

## Open Questions
- **Security/Privacy Risk:** Because email addresses are revealed upon matching a name, an attacker could enumerate or guess names to discover registered email addresses. While rate limiting (5/minute) mitigates brute force, it's still a mild privacy leak. [inferred] This trade-off was likely accepted due to the low-stakes nature of a family wishlist app.
- **Support Contact:** When multiple matches occur, the user is told to "contact support", but no support link or email is provided in the message.
- **Login Redirect Quirk:** The direct login button in the found state sends a POST request to `/login` with the `email`, but the `/login` route expects both `email` and `password` (family code) in a POST. The template does not include a password field in this hidden form. Thus, clicking "Log in as {name}" directly will result in an "Incorrect Family Code" flash error and render `login.html` with the email pre-filled, essentially forcing the user to type the Family Code there. While it ultimately pre-fills the login form, the user experience involves an unexpected error flash.
