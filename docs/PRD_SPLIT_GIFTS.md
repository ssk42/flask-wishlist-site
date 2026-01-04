# PRD: Split Gifts Feature

**Author:** Claude Code
**Created:** 2026-01-04
**Status:** Draft
**Related Improvement:** #32 (Split Gifts)
**Related PRD:** [PRD_ITEM_VARIANTS.md](PRD_ITEM_VARIANTS.md) - Quantity field interaction
**Estimated Effort:** 3-4 hours

---

## 1. Overview

### 1.1 Problem Statement

Some wishlist items are expensive enough that one family member may not want to (or be able to) cover the entire cost alone:

- A $500 gaming console where 3 siblings want to contribute
- A $200 kitchen appliance where grandparents and parents split
- A $150 concert ticket where cousins go in together

Currently, the app only supports single-person claims. Families resort to:
- External coordination (group texts, spreadsheets)
- One person claiming and collecting cash from others
- Awkward "I'll handle part of it" conversations

### 1.2 Proposed Solution

Enable **multiple contributors** to claim portions of a single item with:
- A "Split this gift" option on expensive items
- Contribution tracking (who's in, for how much)
- Coordination comments visible to contributors
- Progress indicator showing funding status

### 1.3 Success Metrics

| Metric | Target |
|--------|--------|
| Split gift adoption | 10% of items over $100 use split |
| Average contributors per split | 2.5+ people |
| Completion rate | 80% of split gifts reach "Purchased" |
| Coordination overhead | No increase in "who's buying what" confusion |

---

## 2. User Stories

### 2.1 Initiating a Split

> **As a gift giver**, I want to propose splitting an expensive gift, so others can join in without me fronting the full cost.

> **As a gift giver**, I want to see which items are available for splitting, so I can find opportunities to contribute smaller amounts.

### 2.2 Contributing to a Split

> **As a contributor**, I want to pledge a specific dollar amount toward a split gift, so I'm not committed to more than I can afford.

> **As a contributor**, I want to see who else is contributing and how much remains, so I know if more help is needed.

### 2.3 Coordination

> **As a split organizer**, I want to communicate with other contributors, so we can coordinate purchasing and delivery.

> **As a contributor**, I want to withdraw my contribution if plans change, so I'm not locked into a commitment.

### 2.4 Completion

> **As a split organizer**, I want to mark the gift as purchased when we've collected enough, so the item owner knows it's handled.

---

## 3. Functional Requirements

### 3.1 Split Gift States

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│  Available  │────▶│ Splitting    │────▶│ Purchased  │
└─────────────┘     └──────────────┘     └────────────┘
       │                   │
       │                   ▼
       │            ┌──────────────┐
       └───────────▶│   Claimed    │  (traditional single-claim)
                    └──────────────┘
```

| Status | Description |
|--------|-------------|
| `Available` | No one has claimed; eligible for split or single claim |
| `Splitting` | One or more contributors pledged; accepting more |
| `Claimed` | Traditional single-person claim (existing behavior) |
| `Purchased` | Gift has been bought (split or single) |

### 3.2 Contribution Model

#### 3.2.1 Starting a Split

- Any non-owner can start a split on an `Available` item
- Initiator becomes the **organizer** (can mark as purchased)
- Initiator pledges their initial contribution amount
- Item status changes to `Splitting`

#### 3.2.2 Joining a Split

- Other non-owners can join an active split
- Each contributor pledges a dollar amount
- No maximum contributors (practical limit ~10)
- Minimum contribution: $1

#### 3.2.3 Contribution Tracking

| Field | Description |
|-------|-------------|
| `contributor_id` | User who pledged |
| `amount` | Dollar amount pledged |
| `is_organizer` | Boolean; first contributor = organizer |
| `created_at` | When contribution was added |

#### 3.2.4 Withdrawing

- Contributors can withdraw before item is purchased
- If organizer withdraws, next contributor becomes organizer
- If last contributor withdraws, item returns to `Available`

### 3.3 Display Requirements

#### 3.3.1 Item Card - Splitting State

```
┌─────────────────────────────────────────────────────────┐
│ [Image]                                                 │
│                                                         │
│ Nintendo Switch OLED                                    │
│ Electronics • High Priority                             │
│ $349.99                                                 │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🤝 SPLITTING: $250 of $350 pledged (71%)            │ │
│ │ ████████████████████░░░░░░░░                        │ │
│ │                                                     │ │
│ │ Contributors:                                       │ │
│ │ • Sarah (organizer): $100                          │ │
│ │ • Mike: $75                                        │ │
│ │ • Dad: $75                                         │ │
│ │                                                     │ │
│ │ [+ Join Split ($100 remaining)]                    │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 💬 Comments (2) - Coordination chat                     │
└─────────────────────────────────────────────────────────┘
```

#### 3.3.2 Split Badge on Item Cards

Items in `Splitting` state show a distinctive badge:

```
🤝 Splitting (71%)
```

#### 3.3.3 My Claims Page - Split Contributions

```
┌─────────────────────────────────────────────────────────┐
│ My Claims                                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Summary                                                 │
│ ┌─────────┬─────────┬─────────┐                        │
│ │ Claimed │ Splits  │Purchased│                        │
│ │    2    │    3    │    5    │                        │
│ └─────────┴─────────┴─────────┘                        │
│                                                         │
│ Split Contributions                                     │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Nintendo Switch for Tommy        Your pledge: $100  │ │
│ │ 🤝 71% funded • 3 contributors                      │ │
│ │ [View Details] [Withdraw]                           │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 3.4 Interaction Flows

#### 3.4.1 Start Split Flow

1. User clicks "Split this gift" on Available item
2. Modal appears: "How much will you contribute?"
3. User enters amount (default: item price ÷ 2)
4. Confirmation: "You're starting a split for $X. Others can join."
5. Item status → `Splitting`, contribution recorded

#### 3.4.2 Join Split Flow

1. User clicks "Join Split" on Splitting item
2. Modal shows: current contributors, remaining amount
3. User enters their pledge amount
4. Confirmation: "You're contributing $X to this gift."
5. Contribution recorded, progress bar updates

#### 3.4.3 Complete Split Flow

1. Organizer clicks "Mark as Purchased" when ready
2. Confirmation: "Mark this gift as purchased? All contributors will be notified."
3. Item status → `Purchased`
4. Notification sent to all contributors

### 3.5 Surprise Protection

**Critical**: The item owner must NEVER see:
- That their item is being split
- Who is contributing
- Contribution amounts
- Split progress percentage

From the owner's perspective, a `Splitting` item appears identical to `Available`.

### 3.6 Access Control Matrix

| Action | Owner | Non-Owner | Contributor | Organizer |
|--------|-------|-----------|-------------|-----------|
| See split status | ❌ | ✅ | ✅ | ✅ |
| Start split | ❌ | ✅ | - | - |
| Join split | ❌ | ✅ | - | - |
| See contributors | ❌ | ✅ | ✅ | ✅ |
| Add comment | ❌ | ✅ | ✅ | ✅ |
| Withdraw | ❌ | ❌ | ✅ | ✅ |
| Mark purchased | ❌ | ❌ | ❌ | ✅ |

---

## 4. Technical Design

### 4.1 Database Changes

#### 4.1.1 New `Contribution` Model

```python
class Contribution(db.Model):
    """Tracks contributions to split gifts."""
    __tablename__ = 'contributions'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    is_organizer = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    item = db.relationship('Item', backref=db.backref('contributions', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref='contributions')

    __table_args__ = (
        db.UniqueConstraint('item_id', 'user_id', name='unique_contribution'),
    )
```

#### 4.1.2 Update Item Model

Add new status value and helper properties:

```python
# Item model additions
@property
def is_splitting(self):
    return self.status == 'Splitting'

@property
def total_pledged(self):
    return sum(c.amount for c in self.contributions)

@property
def split_progress(self):
    if not self.price or self.price == 0:
        return 0
    return min(100, int((self.total_pledged / self.price) * 100))

@property
def remaining_amount(self):
    if not self.price:
        return 0
    return max(0, self.price - self.total_pledged)

@property
def organizer(self):
    for c in self.contributions:
        if c.is_organizer:
            return c.user
    return None
```

#### 4.1.3 Migration

```python
"""Add contributions table for split gifts

Revision ID: xxxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('contributions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('is_organizer', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['item.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id', 'user_id', name='unique_contribution')
    )
    op.create_index('ix_contributions_item_id', 'contributions', ['item_id'])

def downgrade():
    op.drop_table('contributions')
```

### 4.2 New Routes

#### 4.2.1 Items Blueprint Additions

```python
# Start a split
POST /items/<item_id>/split
Body: { amount: float }
Response: Redirect or HTMX partial

# Join a split
POST /items/<item_id>/contribute
Body: { amount: float }
Response: Redirect or HTMX partial

# Withdraw contribution
POST /items/<item_id>/withdraw
Response: Redirect or HTMX partial

# Mark split as purchased (organizer only)
POST /items/<item_id>/complete-split
Response: Redirect or HTMX partial
```

### 4.3 Template Changes

| Template | Changes |
|----------|---------|
| `partials/_item_card.html` | Add split status display, join button |
| `my_claims.html` | Add "Split Contributions" section |
| `items_list.html` | Filter option for "Splitting" items |
| New: `_split_modal.html` | Modal for start/join split |
| New: `_split_progress.html` | Reusable progress component |

### 4.4 Notifications

| Event | Recipients | Message |
|-------|------------|---------|
| New contributor joins | All existing contributors | "[Name] joined the split for [Item]" |
| Contributor withdraws | All remaining contributors | "[Name] withdrew from [Item]" |
| Split completed | All contributors | "[Item] has been purchased!" |
| Organizer changed | New organizer | "You're now the organizer for [Item]" |

### 4.5 Status Value Update

Update status choices to include `Splitting`:

```python
STATUS_CHOICES = ['Available', 'Claimed', 'Splitting', 'Purchased']
```

---

## 5. User Interface

### 5.1 Start Split Modal

```
┌─────────────────────────────────────────────────────────┐
│ 🤝 Split This Gift                              [X]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Nintendo Switch OLED                                    │
│ Total price: $349.99                                    │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ How much will you contribute?                           │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ $  [175.00                                    ]     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Quick select: [$50] [$100] [$175] [Half]               │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ You'll be the organizer for this split.                 │
│ Others can join and contribute their share.             │
│ You can mark it purchased when ready.                   │
│                                                         │
│                    [Cancel]  [Start Split]              │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Join Split Modal

```
┌─────────────────────────────────────────────────────────┐
│ 🤝 Join Split Gift                              [X]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Nintendo Switch OLED for Tommy                          │
│ Total: $349.99 • Remaining: $99.99                      │
│                                                         │
│ ████████████████████████░░░░░░░  71% funded             │
│                                                         │
│ Current contributors:                                   │
│ • Sarah (organizer): $100.00                           │
│ • Mike: $75.00                                         │
│ • Dad: $75.00                                          │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ Your contribution:                                      │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ $  [99.99                                     ]     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Quick select: [$25] [$50] [$99.99 (remaining)]         │
│                                                         │
│                     [Cancel]  [Join Split]              │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Item Card - Splitting State (Non-Owner View)

```
┌─────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────┐ │
│ │                    [Product Image]                  │ │
│ │  [Tommy]                                 [High]     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Nintendo Switch OLED                                    │
│ 🏷️ Electronics                                          │
│ $349.99                                                 │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🤝 SPLITTING                                        │ │
│ │ ████████████████████████░░░░░░░  71%                │ │
│ │ $250 of $350 • 3 contributors                       │ │
│ │                                                     │ │
│ │ [Join ($100 left)]  [👁️ Details]                   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ───────────────────────────────────────────────────── │
│ 💬 Comments (2)                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.4 Item Card - Owner View (Surprise Protected)

```
┌─────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────┐ │
│ │                    [Product Image]                  │ │
│ │  [Your Item]                             [High]     │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Nintendo Switch OLED                                    │
│ 🏷️ Electronics                                          │
│ $349.99                                                 │
│                                                         │
│ ───────────────────────────────────────────────────── │
│ [Edit]                                      [Delete]    │
└─────────────────────────────────────────────────────────┘

(No indication of splitting - appears as normal Available item)
```

---

## 6. Implementation Plan

### Phase 1: Data Model (45 min)
1. Create `Contribution` model in `models.py`
2. Add helper properties to `Item` model
3. Update `STATUS_CHOICES` to include 'Splitting'
4. Create and run migration
5. Write model unit tests

### Phase 2: Routes (1 hour)
1. Implement `start_split` route
2. Implement `join_split` route
3. Implement `withdraw` route
4. Implement `complete_split` route
5. Add HTMX support for all routes
6. Write route unit tests

### Phase 3: Templates (1.5 hours)
1. Create `_split_modal.html` partial
2. Create `_split_progress.html` partial
3. Update `_item_card.html` with split display
4. Update `my_claims.html` with split section
5. Add split filter to `items_list.html`
6. Ensure surprise protection in all views

### Phase 4: Notifications & Polish (45 min)
1. Add notification triggers for split events
2. Browser tests for split flows
3. Edge case handling (price changes, deletions)
4. UI polish and accessibility

**Total Estimated Effort:** 3-4 hours

---

## 7. Testing Requirements

### 7.1 Unit Tests

| Test Case | Expected Result |
|-----------|-----------------|
| Start split on available item | Status → Splitting, contribution created |
| Start split on own item | Rejected with error |
| Start split on claimed item | Rejected with error |
| Join existing split | New contribution added |
| Join split already contributing to | Rejected (unique constraint) |
| Withdraw contribution | Contribution deleted |
| Withdraw as last contributor | Status → Available |
| Organizer withdraws | Next contributor becomes organizer |
| Complete split (organizer) | Status → Purchased |
| Complete split (non-organizer) | Rejected |
| Owner views splitting item | Appears as Available |
| Non-owner views splitting item | Shows split progress |

### 7.2 Browser Tests

| Flow | Steps |
|------|-------|
| Full split lifecycle | Start split → Join → Complete → Verify purchased |
| Withdraw flow | Start split → Withdraw → Verify available |
| Surprise protection | Login as owner → Verify no split indicators |
| My Claims display | Contribute to split → Check my claims page |

### 7.3 Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Item deleted while splitting | Contributions cascade deleted |
| Item price changed while splitting | Progress recalculates; may exceed 100% |
| Contribution exceeds remaining | Allowed (overfunding is OK) |
| Item has no price | Split not available (need price for progress) |

---

## 8. Future Considerations

### 8.1 Out of Scope (V1)

- Actual payment collection (Venmo/PayPal integration)
- Contribution reminders
- Split templates ("split evenly among X people")
- Percentage-based contributions
- Minimum funding threshold before purchase
- Split history/audit log

### 8.2 Potential V2 Features

- **Payment integration**: Link to Venmo/PayPal for actual money transfer
- **Smart suggestions**: "This item is expensive—consider splitting?"
- **Split templates**: "Split 3 ways" auto-calculates amounts
- **Funding thresholds**: Don't allow purchase until 100% funded
- **Partial claims**: Split only part of the cost, single-claim the rest
- **Split invites**: Direct invite specific family members to join

### 8.3 Integration with Item Variants (Quantity Field)

The [Item Variants PRD](PRD_ITEM_VARIANTS.md) introduces a `quantity` field. When an item has `quantity > 1`, interesting scenarios arise for splitting:

#### Scenario: "I want 3 sets of nice wine glasses ($50 each = $150 total)"

**Option A: Split the Total Cost (Recommended for V1)**
- Treat the item as a single $150 purchase
- Contributors split the total regardless of quantity
- Simple: no changes to Split Gifts model
- Display: "3× Wine Glasses - $150 total"

**Option B: Split by Unit (V2 Consideration)**
- Each unit can be claimed/split independently
- Example: Mom claims 1 set, Dad & Uncle split 1 set, Grandma claims 1 set
- Requires: `Contribution.quantity_claimed` field or per-unit tracking
- More complex but more flexible for consumables

#### Recommended Approach

**V1**: Ignore quantity for splitting purposes. The `quantity` field is informational ("I want 3 of these") but splitting applies to total item cost.

**V2**: Consider "per-unit claiming" where:
```python
# Potential V2 model extension
class Contribution(db.Model):
    # ... existing fields ...
    units_claimed = db.Column(db.Integer, default=None)  # None = splitting by cost
```

This would enable:
- "Claim 1 of 3" for quantity items
- Mixed mode: 1 unit claimed outright, 2 units being split
- Progress display: "2 of 3 units claimed, 1 unit splitting (67%)"

#### UI Consideration

When an item has both `quantity > 1` AND is being split, show clear messaging:

```
┌─────────────────────────────────────────────────────────┐
│ Wine Glasses (×3)                                       │
│ $50 each • $150 total                                   │
│                                                         │
│ 🤝 SPLITTING TOTAL COST                                 │
│ ████████████████░░░░░░░░  67%                          │
│ $100 of $150 pledged                                    │
│                                                         │
│ Note: All 3 sets will be purchased together             │
└─────────────────────────────────────────────────────────┘
```

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Surprise protection leak | Ruins gift surprises | Comprehensive testing; status appears as Available to owner |
| Coordination breakdown | Gift not purchased | Comments section for contributor chat; notifications |
| Overfunding confusion | Awkward money situations | Allow overfunding; contributors sort it out |
| Abandoned splits | Items stuck in Splitting | Consider auto-timeout after 60 days (V2) |
| Organizer goes AWOL | Can't complete purchase | Any contributor can become organizer if needed (V2) |

---

## 10. Appendix

### 10.1 Alternative Designs Considered

#### Option A: Percentage-Based Contributions
- Contributors pledge percentages instead of dollars
- Pro: Automatically adjusts if price changes
- Con: More abstract, harder to understand
- **Decision**: Dollar amounts are more intuitive

#### Option B: Pre-Set Split Groups
- Owner defines "split this 3 ways" upfront
- Pro: Clear expectations
- Con: Restricts flexibility, requires owner involvement
- **Decision**: Open contribution is more flexible

#### Option C: No Organizer Role
- Any contributor can mark as purchased
- Pro: Simpler model
- Con: Risk of premature completion
- **Decision**: Organizer role adds accountability

### 10.2 Surprise Protection Implementation

```python
# In template rendering context
def get_display_status(item, current_user):
    """Return display-safe status for surprise protection."""
    if item.user_id == current_user.id:
        # Owner sees Splitting as Available
        if item.status == 'Splitting':
            return 'Available'
        # Owner sees Claimed/Purchased as Available too (existing behavior)
        if item.status in ['Claimed', 'Purchased']:
            return 'Available'
    return item.status
```

### 10.3 Related Documentation

- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Project roadmap
- [models.py](../models.py) - Database models
- [blueprints/items.py](../blueprints/items.py) - Items routes
- [PRD_ITEM_VARIANTS.md](PRD_ITEM_VARIANTS.md) - Related feature (variants work with splits)
