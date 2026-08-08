# Price Stealth EARS Specifications

## Identity Management
- [x] **AUTO-STL-001**: While fetching prices, the system SHALL use a browser identity that is not currently marked as burned.
- [x] **AUTO-STL-002**: If an identity reaches between 10 and 20 requests (randomized), the system SHALL clear its cookies and reset its request count to rotate its session.
- [x] **AUTO-STL-003**: When an identity encounters a CAPTCHA or robot check, the system SHALL mark the identity as burned for 24 hours.
- [x] **AUTO-STL-004**: If all identities are burned, the system SHALL return a failure indicating no healthy identities are available (currently logged as warning and returns None).
- [x] **AUTO-STL-005**: The system SHALL save and load identity cookies from Redis to persist sessions across runs.

## Stealth Extraction
- [x] **AUTO-STL-006**: When launching a browser context, the system SHALL apply the Playwright Stealth plugin and configure the context matching the identity's fingerprint (User-Agent, Viewport, Locale, Timezone, WebGL, Device Scale).
- [x] **AUTO-STL-007**: While extracting a price, if the system encounters a 429 or 503 HTTP status code, it SHALL classify the failure as RATE_LIMITED.
- [x] **AUTO-STL-008**: While extracting a price, if the system encounters "captcha" or "robot check" in the page content, it SHALL classify the failure as CAPTCHA.

## Human-like Behavior
- [x] **AUTO-STL-009**: When interacting with the page, the system SHALL simulate human-like mouse movements using a quadratic bezier curve with randomized noise.
- [x] **AUTO-STL-010**: When interacting with the page, the system SHALL simulate human scrolling by moving the wheel in variable chunks with random delays.
- [x] **AUTO-STL-011**: The system SHALL attempt to dismiss cookie banners by looking for and clicking known Amazon cookie consent selectors (e.g., `#sp-cc-accept`).
- [x] **AUTO-STL-012**: Before attempting data extraction, the system SHALL simulate a human reading delay of 1000ms +/- 40%.
