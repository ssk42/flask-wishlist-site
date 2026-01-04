# PRD: Secret Santa Mode

**Author:** Claude Code
**Created:** 2026-01-04
**Status:** Draft
**Related Improvement:** #50 (New - Secret Santa Mode)
**Related Features:** Events (#34), Wishlist Sharing, Surprise Protection
**Estimated Effort:** 6-8 hours

---

## 1. Overview

### 1.1 Problem Statement

Families often organize Secret Santa gift exchanges for holidays, but coordination is challenging:

- **Manual assignment**: Someone has to draw names, ensure no one gets themselves, handle exclusions (spouses shouldn't get each other)
- **Secrecy leaks**: The organizer knows all assignments; physical draws can be peeked at
- **Wishlist disconnect**: Assignments happen separately from the wishlist app, so givers have to ask around for gift ideas
- **No budget guidance**: People may overspend or underspend without agreed limits

### 1.2 Proposed Solution

Add a **Secret Santa mode** to Events that:
- Randomly assigns each participant to buy for exactly one other participant
- Integrates with existing wishlists so givers can see their recipient's wishes
- Supports exclusion rules (e.g., couples shouldn't draw each other)
- Enforces optional budget limits
- Maintains complete secrecy until reveal

### 1.3 Success Metrics

| Metric | Target |
|--------|--------|
| Secret Santa events created | 2+ per family during holiday season |
| Assignment completion rate | 95% of participants view their assignment |
| Gift completion rate | 90% of assignments result in a claimed item |
| User satisfaction | No complaints about broken secrecy |

---

## 2. User Stories

### 2.1 Event Organizer

> **As an event organizer**, I want to create a Secret Santa event and invite family members, so we can do a gift exchange.

> **As an organizer**, I want to set exclusion rules (like "spouses can't draw each other"), so assignments are fair.

> **As an organizer**, I want to set a budget limit, so everyone knows how much to spend.

> **As an organizer**, I want to trigger the random assignment when everyone has joined, so the exchange can begin.

> **As an organizer**, I want to reveal all assignments after the event, so we can see who had whom.

### 2.2 Participant

> **As a participant**, I want to join a Secret Santa event with a code, so I can be included in the draw.

> **As a participant**, I want to see who I'm buying for and view their wishlist, so I can find the perfect gift.

> **As a participant**, I want my assignment to be completely secret from everyone else, including the organizer.

> **As a participant**, I want to mark my gift as purchased, so I can track my progress.

---

## 3. Functional Requirements

### 3.1 Event Enhancement

Extend the existing Event model with Secret Santa capabilities:

| Field | Type | Description |
|-------|------|-------------|
| `is_secret_santa` | Boolean | Whether this event uses Secret Santa mode |
| `budget_min` | Float | Minimum gift budget (optional) |
| `budget_max` | Float | Maximum gift budget (optional) |
| `join_code` | String(8) | Unique code for participants to join |
| `assignments_locked` | Boolean | Whether random draw has occurred |
| `revealed` | Boolean | Whether assignments are visible to all |

### 3.2 Participant Management

New model to track Secret Santa participants:

```
SecretSantaParticipant
├── id
├── event_id (FK → Event)
├── user_id (FK → User)
├── assigned_to_id (FK → User, nullable)
├── gift_status: 'pending' | 'purchased' | 'delivered'
├── joined_at
└── exclusions (JSON array of user_ids)
```

### 3.3 Core Flows

#### 3.3.1 Create Secret Santa Event

1. Organizer creates event with "Enable Secret Santa" checkbox
2. System generates unique 8-character join code
3. Organizer optionally sets budget range ($20-$50)
4. Organizer optionally adds exclusion rules
5. Event is created in "gathering participants" state

#### 3.3.2 Join Event

1. Participant enters join code on Secret Santa page
2. System validates code and adds participant
3. Participant can set their own exclusions (optional)
4. Participant sees "Waiting for draw..." status

#### 3.3.3 Run the Draw

1. Organizer clicks "Run Secret Santa Draw" when ready
2. System validates:
   - Minimum 3 participants
   - Exclusions don't make assignment impossible
3. System runs randomized assignment algorithm
4. Assignments are stored encrypted (organizer cannot see)
5. All participants notified: "Your Secret Santa assignment is ready!"

#### 3.3.4 View Assignment

1. Participant clicks "View My Assignment"
2. System shows: recipient name + link to their wishlist
3. Budget reminder displayed
4. "Mark as Purchased" button available
5. Participant can filter recipient's wishlist by budget

#### 3.3.5 Reveal (Post-Event)

1. After event date, organizer can trigger reveal
2. All assignments become visible to all participants
3. Shows: "Sarah → Mike → Grandma → Dad → Sarah" chain

### 3.4 Assignment Algorithm

```python
def assign_secret_santa(participants, exclusions):
    """
    Derangement algorithm with exclusion constraints.
    Returns dict of {giver_id: recipient_id}
    """
    # Create valid recipient pool for each giver
    # Use backtracking if simple shuffle fails
    # Guarantee: no self-assignment, respect exclusions
    # Guarantee: everyone gives to exactly one person
    # Guarantee: everyone receives from exactly one person
```

**Constraints:**
- No self-assignment
- Exclusion pairs cannot be assigned to each other
- Must form a complete cycle (everyone gives and receives)
- Algorithm must handle edge cases (small groups, many exclusions)

### 3.5 Secrecy Model

**Critical**: Assignments must be cryptographically protected:

| Who | Can See |
|-----|---------|
| Participant | Only their own assignment |
| Organizer | Participant list, but NOT assignments |
| Other participants | Nothing about assignments |
| After reveal | Everyone sees all assignments |

**Implementation**: Store `assigned_to_id` encrypted with participant's session key, or use a reveal-only approach where assignments aren't stored until reveal.

### 3.6 Wishlist Integration

When viewing assignment:
- Show recipient's wishlist items (respecting normal visibility)
- Filter items by budget range (if set)
- Show items NOT already claimed by others
- Allow claiming directly from assignment view
- "Claimed for Secret Santa" badge (visible only to claimer)

---

## 4. Technical Design

### 4.1 Database Changes

#### 4.1.1 Event Model Updates

```python
# Add to Event model
is_secret_santa = db.Column(db.Boolean, default=False, nullable=False)
budget_min = db.Column(db.Float, nullable=True)
budget_max = db.Column(db.Float, nullable=True)
join_code = db.Column(db.String(8), unique=True, nullable=True, index=True)
assignments_locked = db.Column(db.Boolean, default=False, nullable=False)
revealed = db.Column(db.Boolean, default=False, nullable=False)
```

#### 4.1.2 New SecretSantaParticipant Model

```python
class SecretSantaParticipant(db.Model):
    __tablename__ = 'secret_santa_participants'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    gift_status = db.Column(db.String(20), default='pending', nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    exclusions = db.Column(db.JSON, default=list)

    # Relationships
    event = db.relationship('Event', backref='participants')
    user = db.relationship('User', foreign_keys=[user_id])
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id])

    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='unique_participant'),
    )
```

### 4.2 New Routes

#### 4.2.1 Secret Santa Blueprint

```python
# blueprints/secret_santa.py

GET  /secret-santa                      # List user's SS events
GET  /secret-santa/join                 # Join form
POST /secret-santa/join                 # Process join code
GET  /secret-santa/<event_id>           # Event dashboard
POST /secret-santa/<event_id>/draw      # Run assignment (organizer)
GET  /secret-santa/<event_id>/assignment # View my assignment
POST /secret-santa/<event_id>/reveal    # Reveal all (organizer)
POST /secret-santa/<event_id>/exclusion # Add exclusion rule
```

#### 4.2.2 Event Blueprint Updates

```python
# Modify new_event route to handle Secret Santa options
# Add is_secret_santa, budget_min, budget_max to form
```

### 4.3 Template Changes

| Template | Purpose |
|----------|---------|
| `event_form.html` | Add Secret Santa toggle, budget fields |
| `secret_santa_dashboard.html` | Participant list, draw button, status |
| `secret_santa_assignment.html` | Show assignment + wishlist |
| `secret_santa_join.html` | Enter join code form |
| `secret_santa_reveal.html` | Post-event assignment chain |

### 4.4 Assignment Algorithm

```python
import random
from typing import Dict, List, Set

def generate_assignments(
    participants: List[int],
    exclusions: Dict[int, Set[int]]
) -> Dict[int, int]:
    """
    Generate valid Secret Santa assignments.

    Args:
        participants: List of user IDs
        exclusions: Dict mapping user_id to set of excluded recipient IDs

    Returns:
        Dict mapping giver_id to recipient_id

    Raises:
        ValueError: If valid assignment is impossible
    """
    n = len(participants)
    if n < 3:
        raise ValueError("Need at least 3 participants")

    # Build exclusion sets (include self)
    full_exclusions = {
        p: exclusions.get(p, set()) | {p}
        for p in participants
    }

    # Try up to 1000 times to find valid derangement
    for _ in range(1000):
        shuffled = participants.copy()
        random.shuffle(shuffled)

        # Check if this shuffle works
        valid = True
        for i, giver in enumerate(participants):
            recipient = shuffled[i]
            if recipient in full_exclusions[giver]:
                valid = False
                break

        if valid:
            return {
                participants[i]: shuffled[i]
                for i in range(n)
            }

    raise ValueError("Cannot generate valid assignments with given exclusions")
```

### 4.5 Notifications

| Event | Recipients | Message |
|-------|------------|---------|
| Participant joins | Organizer | "[Name] joined your Secret Santa!" |
| Draw completed | All participants | "Your Secret Santa assignment is ready!" |
| Reminder (3 days before) | Unpurchased participants | "Don't forget to get your Secret Santa gift!" |
| Reveal triggered | All participants | "Secret Santa assignments revealed!" |

---

## 5. User Interface

### 5.1 Event Form with Secret Santa Toggle

```
┌─────────────────────────────────────────────────────────┐
│ Create New Event                                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Event Name *                                            │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Family Christmas 2026                               │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Date *                                                  │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 2026-12-25                                          │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ☑ Enable Secret Santa Mode                          │ │
│ │                                                     │ │
│ │ Budget Range (optional)                             │ │
│ │ ┌──────────┐    ┌──────────┐                       │ │
│ │ │ $ 25     │ to │ $ 50     │                       │ │
│ │ └──────────┘    └──────────┘                       │ │
│ │                                                     │ │
│ │ ℹ️ A join code will be generated for participants   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│                           [Cancel]  [Create Event]      │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Secret Santa Dashboard (Organizer View)

```
┌─────────────────────────────────────────────────────────┐
│ 🎅 Family Christmas 2026 - Secret Santa                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Join Code: XMAS2026                    [📋 Copy]       │
│ Budget: $25 - $50                                       │
│ Status: Gathering Participants                          │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ Participants (5)                                        │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ✓ Sarah (you - organizer)                          │ │
│ │ ✓ Mike                                              │ │
│ │ ✓ Mom                                               │ │
│ │ ✓ Dad                                               │ │
│ │ ✓ Grandma                                           │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Exclusions                                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Mom ↔ Dad (spouses)                    [Remove]    │ │
│ │ Sarah ↔ Mike (spouses)                 [Remove]    │ │
│ │                                                     │ │
│ │ [+ Add Exclusion]                                   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ Ready to draw? Everyone will be randomly assigned.      │
│                                                         │
│              [🎲 Run Secret Santa Draw]                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Assignment View (Participant)

```
┌─────────────────────────────────────────────────────────┐
│ 🎁 Your Secret Santa Assignment                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ You are buying a gift for:                              │
│                                                         │
│           ┌───────────────────┐                         │
│           │      👤           │                         │
│           │     GRANDMA       │                         │
│           └───────────────────┘                         │
│                                                         │
│ Budget: $25 - $50                                       │
│ Event: December 25, 2026                                │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ Grandma's Wishlist (items in budget)                    │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📦 Cozy Reading Socks              $28.99           │ │
│ │ Available • [Claim for Secret Santa]               │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ 📦 Puzzle Book Collection           $24.99          │ │
│ │ Available • [Claim for Secret Santa]               │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ 📦 Fancy Tea Sampler                $35.00          │ │
│ │ Available • [Claim for Secret Santa]               │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ [View Full Wishlist]                                    │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ Your Status: ⏳ Gift not yet purchased                  │
│                                                         │
│ [✓ Mark Gift as Purchased]                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.4 Reveal View (Post-Event)

```
┌─────────────────────────────────────────────────────────┐
│ 🎅 Family Christmas 2026 - Reveal!                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ The Secret Santa assignments were:                      │
│                                                         │
│    Sarah  ──🎁──▶  Grandma                             │
│      ▲                │                                 │
│      │                ▼                                 │
│    Dad    ◀──🎁──   Mom                                │
│      │                ▲                                 │
│      ▼                │                                 │
│    Mike   ──🎁──▶   Dad                                │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ Gift Status                                             │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Sarah → Grandma: ✅ Delivered (Cozy Socks)          │ │
│ │ Mike → Dad: ✅ Delivered (Tool Set)                 │ │
│ │ Grandma → Mom: ✅ Delivered (Scarf)                 │ │
│ │ Mom → Sarah: ✅ Delivered (Book)                    │ │
│ │ Dad → Mike: ✅ Delivered (Game)                     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 🎉 Everyone received a gift!                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Plan

### Phase 1: Data Model (1 hour)
1. Add Secret Santa fields to Event model
2. Create SecretSantaParticipant model
3. Create and run migration
4. Write model unit tests

### Phase 2: Join & Manage (2 hours)
1. Create secret_santa blueprint
2. Implement join code generation and validation
3. Build participant management UI
4. Implement exclusion rules
5. Add organizer controls

### Phase 3: Assignment Algorithm (1.5 hours)
1. Implement derangement algorithm with exclusions
2. Add constraint validation
3. Store assignments securely
4. Write algorithm unit tests
5. Handle edge cases (impossible assignments)

### Phase 4: Assignment View & Integration (2 hours)
1. Build assignment reveal UI
2. Integrate with wishlist display
3. Add budget filtering
4. Implement claim-for-secret-santa flow
5. Add gift status tracking

### Phase 5: Reveal & Polish (1.5 hours)
1. Implement post-event reveal
2. Add notification triggers
3. Browser tests for full flow
4. Edge case handling

**Total Estimated Effort:** 6-8 hours

---

## 7. Testing Requirements

### 7.1 Unit Tests

| Test Case | Expected Result |
|-----------|-----------------|
| Create SS event | Generates unique join code |
| Join with valid code | Adds participant |
| Join with invalid code | Returns error |
| Join twice | Rejected (unique constraint) |
| Run draw with < 3 participants | Returns error |
| Run draw with valid group | All assigned, no self-assignments |
| Run draw with exclusions | Respects exclusion rules |
| Impossible exclusions | Returns error message |
| View own assignment | Shows correct recipient |
| View others' assignment | Denied |
| Organizer view assignments | Denied (before reveal) |
| Reveal after event | All assignments visible |

### 7.2 Algorithm Tests

| Scenario | Expected |
|----------|----------|
| 3 participants, no exclusions | Valid cycle |
| 5 participants, 2 exclusion pairs | Valid assignments |
| 4 participants, too many exclusions | Error raised |
| Large group (20 people) | Completes in < 1 second |
| Randomness | Different results on multiple runs |

### 7.3 Browser Tests

| Flow | Steps |
|------|-------|
| Full Secret Santa flow | Create event → Participants join → Run draw → View assignments → Mark purchased → Reveal |
| Join flow | Enter code → See waiting status → See assignment after draw |
| Exclusion flow | Add exclusion → Run draw → Verify exclusion respected |

---

## 8. Future Considerations

### 8.1 Out of Scope (V1)

- Anonymous messaging to recipient ("hints")
- Wish intensity/priority preferences
- Re-draw functionality (if someone drops out)
- Cross-family Secret Santa (multiple families)
- Secret Santa history (past years)
- Physical gift tracking (shipped/delivered)

### 8.2 Potential V2 Features

- **Gift hints**: Anonymous way to ask "would you prefer X or Y?"
- **Reminder customization**: Set reminder schedule
- **Theme/rules**: "Handmade only" or "Experience gifts only"
- **White Elephant mode**: Variant with gift stealing
- **Wishlist priorities**: Recipient can mark "really want this"
- **Photo reveal**: Upload photo of gift for reveal page

### 8.3 Integration with Other PRDs

| PRD | Integration Point |
|-----|-------------------|
| Item Variants | Budget filtering considers size/color availability |
| Split Gifts | Could allow two people to split a Secret Santa gift (unusual but possible) |
| Wishlist Sharing | Secret Santa assignment view is a specialized share |

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Secrecy leak (organizer sees) | Ruins surprise | Don't store assignments in readable form until reveal |
| Impossible assignment | Can't run event | Validate exclusions before draw; clear error messages |
| Last-minute dropouts | Incomplete chain | Lock participants before draw; no withdrawal after |
| Algorithm bias | Unfair assignments | Use cryptographically random shuffling |
| Join code guessing | Unauthorized joins | 8-char alphanumeric = 2.8 trillion combinations |
| Participant forgets | No gift purchased | Email reminders; status dashboard |

---

## 10. Appendix

### 10.1 Join Code Generation

```python
import secrets
import string

def generate_join_code(length=8):
    """Generate a unique, readable join code."""
    # Use uppercase + digits, excluding confusing chars (0, O, I, 1)
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))
```

### 10.2 Exclusion Data Structure

```python
# Stored as JSON in participant record
exclusions = [
    {"type": "mutual", "user_ids": [1, 2], "reason": "spouses"},
    {"type": "one_way", "from_id": 3, "to_id": 4, "reason": "already know gift"}
]
```

### 10.3 Related Documentation

- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Project roadmap
- [models.py](../models.py) - Database models
- [blueprints/events.py](../blueprints/events.py) - Events routes
- [PRD_WISHLIST_SHARING.md](PRD_WISHLIST_SHARING.md) - Sharing patterns
