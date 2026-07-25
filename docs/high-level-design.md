# High-Level Design (HLD)

## Core Concept
The Wishlist application is structured around a central invariant: **Surprise Protection**. To guarantee that an item owner cannot deduce the claim or purchase status of their gifts, the system's architecture enforces strict behavioral boundaries depending on the user's role (Owner vs Giver) and the execution context (User vs Autonomous Agent).

## The Behavioral Boundary Lens
The architecture is divided into five top-level boundaries:

### 1. `boundary-auth`
The perimeter defense. It handles entry into the trusted family zone.
- **Segments**: `auth-flow`, `account-recovery`
- **Key Invariants**: Relies on a shared Family Code to allow frictionless access for trusted members while keeping outsiders away. Rate limiting heavily protects this boundary.

### 2. `boundary-owner`
The curation and management context. This is what a user sees when managing their own lists.
- **Segments**: `item-curation`, `event-management`, `owner-visibility`
- **Key Invariants**: The owner must have full CRUD over their items and events. However, `owner-visibility` acts as a one-way mirror—any aggregation, export, or dashboard feed accessed by the owner must mathematically strip out all claim statuses, comment counts, and split-gift progress related to their own items.

### 3. `boundary-giver`
The coordination context. This is where users interact with items they do not own.
- **Segments**: `item-claiming`, `split-contributions`, `secret-coordination`
- **Key Invariants**: Givers can claim items, pool funds for expensive gifts, and leave coordination comments. All state changes here are strictly hidden from the item owner.

### 4. `boundary-viewer`
The presentation and aggregation layer.
- **Segments**: `feed-filtering`, `ui-state`
- **Key Invariants**: Drives the global dashboard and item feeds, applying session-based filters. Must inherently respect the `owner-visibility` masks.

### 5. `boundary-autonomous`
The background processing context, completely detached from HTTP requests.
- **Segments**: `price-stealth`, `price-processing`, `system-tasks`
- **Key Invariants**: Periodically sweeps URLs using rotating stealth Playwright identities to extract prices and record histories. Handles Celery-based async workloads like event reminders.

## Inferred Design Decisions & Technical Debt
During the codebase mapping, several recurring themes and idiosyncrasies were discovered:
- **Coupling of Audit/Business Logic**: `last_updated_by_id` is sometimes overloaded to imply claim actions.
- **Idempotency Limits**: Session-based token sets (like for item forms) are hardcoded to an arbitrary limit (e.g., 20 max).
- **Stealth Brittle-ness**: Target fallbacks and synchronous SQLAlchemy calls in async processing loops represent fragile edge cases in `boundary-autonomous`.

## Taxonomy
Refer to `docs/arrows/index.yaml` for the precise structural mapping of these boundaries to their corresponding Low-Level Designs (LLDs) and EARS Specifications.
