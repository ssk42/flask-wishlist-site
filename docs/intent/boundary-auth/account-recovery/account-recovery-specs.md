# Account Recovery (Forgot Email) Specifications

## Ubiquitous Language
- **Account Recovery**: The process of a user retrieving their registered email address using their name.
- **Found State**: The UI state presented to the user when their name is successfully matched to an email address.
- **Search State**: The initial UI state where a user inputs their name to search for their email.

## EARS Requirements

### Search State & Input Validation
- [x] **AUTH-REC-001**: While on the login page, the user SHALL be able to navigate to the forgot email page via a link.
- [x] **AUTH-REC-002**: When the user requests the forgot email page, the system SHALL render the Search State form.
- [x] **AUTH-REC-003**: When the user submits the search form with an empty name, the system SHALL display a warning "Please enter your name." and remain in the Search State.
- [x] **AUTH-REC-004**: When the user submits the search form, the system SHALL strip leading and trailing whitespace from the submitted name.

### Matching & Recovery
- [x] **AUTH-REC-005**: When the user submits a name, the system SHALL perform a case-insensitive search against the registered users' names.
- [x] **AUTH-REC-006**: If the search results in exactly one match, the system SHALL transition to the Found State, displaying a success message, the user's name, and their registered email address.
- [x] **AUTH-REC-007**: If the search results in no matches, the system SHALL display a danger message "We could not find an account with that name. Please check your spelling or sign up." and remain in the Search State.
- [x] **AUTH-REC-008**: If the search results in multiple matches, the system SHALL display a warning message "We found X accounts with similar names. Please contact support." and remain in the Search State.

### Found State Behavior
- [x] **AUTH-REC-009**: While in the Found State, the system SHALL display a button to log in directly using the found email.
- [x] **AUTH-REC-010**: When the user clicks the direct login button in the Found State, the system SHALL submit the email to the login route (which currently results in pre-filling the login form via an initial failure due to missing family code).

### Security
- [x] **AUTH-REC-011**: When a user attempts to access the forgot email endpoint, the system SHALL limit requests to 5 per minute to prevent enumeration attacks.
