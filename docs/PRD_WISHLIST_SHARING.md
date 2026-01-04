# PRD: Wishlist Sharing Feature

**Author:** Claude Code
**Created:** 2026-01-04
**Status:** Draft
**Related Improvements:** #22 (Wishlist Sharing Links), #47 (External Share Links), #48 (Gift Registry Mode)

---

## 1. Overview

### 1.1 Problem Statement

Currently, the Family Wishlist app requires all users to register with the family code to view any wishlists. This creates barriers for:

1. **Extended family/friends** (e.g., grandparents, aunts, family friends) who want to see a wishlist but shouldn't have full family access
2. **Gift coordinators** who need to share a read-only view without exposing the claim status
3. **Privacy-conscious users** who want to hide their wishlist from certain family members temporarily

### 1.2 Proposed Solution

Implement a tiered sharing system that allows:
- **Privacy controls** for hiding wishlists within the family group
- **Shareable links** for read-only external access without registration

### 1.3 Success Metrics

| Metric | Target |
|--------|--------|
| Users creating share links | 50% of active users within 30 days |
| External link visits | Average 3+ views per shared link |
| Privacy feature adoption | 20% of users adjust privacy settings |
| Support requests | No increase in sharing-related confusion |

---

## 2. User Stories

### 2.1 Privacy Controls (Internal)

> **As a family member**, I want to hide my wishlist from specific family members temporarily, so I can add surprise gifts without them seeing.

> **As a user**, I want to make my wishlist private by default, so only I can see it until I'm ready to share.

### 2.2 External Sharing

> **As a parent**, I want to share my child's wishlist with grandma via a link, so she can see what to buy without creating an account.

> **As a user**, I want to share a read-only version of my wishlist that hides who has claimed items, so the gift surprise is preserved for external viewers too.

> **As a wishlist owner**, I want to revoke a share link at any time, so I can control access if I change my mind.

---

## 3. Functional Requirements

### 3.1 Privacy Levels

Implement a three-tier visibility system for wishlists:

| Level | Visibility | Use Case |
|-------|------------|----------|
| **Private** | Owner only | Drafting wishlist, adding surprise gifts |
| **Family** (default) | All authenticated family members | Standard family sharing |
| **Public Link** | Anyone with the link (read-only) | External sharing |

### 3.2 Share Link Behavior

#### 3.2.1 Link Generation
- Generate unique, unguessable tokens (UUID v4)
- URL format: `/wishlist/share/<token>`
- One active link per user at a time (simplicity)
- Links never expire by default (owner can revoke)

#### 3.2.2 Guest View Experience
- No login required
- Read-only access (no claiming, no comments)
- Shows items with "Available" status only (hides claim info for surprise protection)
- Displays owner's name and wishlist items
- Clean, focused UI without family navigation
- Optional: Filter by event/category

#### 3.2.3 Link Management
- Owner can view their active share link
- Owner can regenerate link (invalidates old one)
- Owner can disable sharing entirely

### 3.3 Privacy Setting Management

#### 3.3.1 User Settings Page
New "Privacy & Sharing" section:
- Toggle: "Make my wishlist private" (hides from family view)
- Share link display with copy button
- "Generate New Link" / "Disable Sharing" buttons
- Visual indicator of current visibility status

#### 3.3.2 Visibility Indicators
- Items list shows privacy badge next to user's name
- Dashboard shows "Private" indicator for hidden wishlists

### 3.4 Access Control Matrix

| Action | Owner | Family (Auth) | Guest (Link) |
|--------|-------|---------------|--------------|
| View items | ✅ | ✅ (if not private) | ✅ (available only) |
| See claimed/purchased status | ❌ (surprise) | ✅ | ❌ |
| Claim items | ✅ | ✅ | ❌ |
| Add comments | ✅ | ✅ | ❌ |
| Edit items | ✅ | ❌ | ❌ |
| See comments | ❌ (surprise) | ✅ | ❌ |

---

## 4. Technical Design

### 4.1 Database Changes

#### 4.1.1 Update User Model

The `is_private` field already exists but is unused. Activate it:

```python
# models.py - User model (existing field)
is_private = db.Column(db.Boolean, default=False, nullable=False)
```

#### 4.1.2 New ShareLink Model

```python
class ShareLink(db.Model):
    __tablename__ = 'share_links'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    token = db.Column(db.String(36), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed_at = db.Column(db.DateTime, nullable=True)
    access_count = db.Column(db.Integer, default=0)

    # Relationship
    user = db.relationship('User', backref=db.backref('share_link', uselist=False))
```

### 4.2 New Routes

#### 4.2.1 Public Share View (No Auth Required)

```
GET /wishlist/share/<token>
```
- Validates token exists and is active
- Returns guest view template with available items only
- Increments access_count, updates last_accessed_at
- Rate limited: 30 requests/minute per IP

#### 4.2.2 Share Management (Auth Required)

```
GET  /settings/sharing          # View sharing settings
POST /settings/sharing/enable   # Generate/regenerate link
POST /settings/sharing/disable  # Deactivate link
POST /settings/privacy          # Toggle is_private
```

### 4.3 Template Changes

#### 4.3.1 New Templates

| Template | Purpose |
|----------|---------|
| `shared_wishlist.html` | Guest view of shared wishlist |
| `settings_sharing.html` | Share management UI |

#### 4.3.2 Modified Templates

| Template | Change |
|----------|--------|
| `items_list.html` | Filter out private users' items |
| `_item_card.html` | Guest-mode variant (no actions) |
| `base.html` | Add sharing link to navbar dropdown |
| `dashboard.html` | Show privacy status indicator |

### 4.4 Security Considerations

1. **Token Security**: UUID v4 tokens (122 bits of entropy)
2. **Rate Limiting**: Prevent enumeration attacks on share URLs
3. **No PII Exposure**: Guest view only shows first name + items
4. **CSRF Protection**: All POST endpoints protected (existing)
5. **Surprise Protection**: Maintained for both family and guest views

### 4.5 Caching Strategy

- Cache shared wishlist pages for 5 minutes (Redis)
- Cache key: `shared_wishlist:{token}`
- Invalidate on: item add/edit/delete, privacy change

---

## 5. User Interface

### 5.1 Share Settings Page Mockup

```
┌─────────────────────────────────────────────────────────┐
│ Privacy & Sharing                                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Wishlist Visibility                                     │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ☐ Make my wishlist private                          │ │
│ │   Only you can see your wishlist when enabled       │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Share with External Friends & Family                    │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Anyone with this link can view your wishlist:       │ │
│ │                                                     │ │
│ │ https://wishlist.app/wishlist/share/abc123...       │ │
│ │                                                     │ │
│ │ [📋 Copy Link]  [🔄 New Link]  [🚫 Disable]         │ │
│ │                                                     │ │
│ │ ℹ️ External viewers see available items only.       │ │
│ │   They cannot see who has claimed items.            │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Link Statistics                                         │
│ • Created: January 4, 2026                              │
│ • Views: 12                                             │
│ • Last accessed: 2 hours ago                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Guest Wishlist View Mockup

```
┌─────────────────────────────────────────────────────────┐
│ 🎁 Sarah's Wishlist                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📦 Kindle Paperwhite                     $139.99    │ │
│ │ Electronics • High Priority                         │ │
│ │ [View on Amazon →]                                  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📦 Cozy Throw Blanket                    $49.99     │ │
│ │ Home • Medium Priority                              │ │
│ │ [View on Target →]                                  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📦 Running Shoes - Size 8                $120.00    │ │
│ │ Clothing • High Priority                            │ │
│ │ "Nike Pegasus, any color"                           │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ ─────────────────────────────────────────────────────── │
│ Shared via Family Wishlist • Sign in to claim items    │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Plan

### Phase 1: Privacy Controls (1-2 hours)
1. Activate `is_private` field in User model
2. Add privacy toggle to user settings
3. Filter private users from items list
4. Add visual privacy indicators

### Phase 2: Share Link Infrastructure (2-3 hours)
1. Create `ShareLink` model and migration
2. Implement token generation/management routes
3. Build sharing settings UI
4. Add link copy functionality

### Phase 3: Guest View (2-3 hours)
1. Create public share route (no auth)
2. Build guest wishlist template
3. Implement available-items-only filtering
4. Add rate limiting
5. Analytics tracking (access count)

### Phase 4: Polish & Testing (1-2 hours)
1. Cache implementation
2. Unit tests for all new routes
3. Browser tests for share flow
4. Security audit

**Total Estimated Effort:** 6-10 hours

---

## 7. Testing Requirements

### 7.1 Unit Tests

| Test Case | Expected Result |
|-----------|-----------------|
| Generate share link | Creates valid UUID token |
| Access valid share link | Returns 200 with items |
| Access invalid/expired link | Returns 404 |
| Access disabled link | Returns 404 |
| Private user hidden from family | Items not in list |
| Guest view hides claimed items | Only available items shown |
| Regenerate link invalidates old | Old token returns 404 |
| Rate limit on share endpoint | Returns 429 after limit |

### 7.2 Browser Tests

| Flow | Steps |
|------|-------|
| Enable sharing | Settings → Enable → Copy link → Verify link works |
| Disable sharing | Settings → Disable → Old link returns error |
| Privacy toggle | Enable private → Verify hidden from other users |
| Guest experience | Access share link → Verify read-only, no claim buttons |

---

## 8. Future Considerations

### 8.1 Out of Scope (V1)

- Multiple share links per user
- Link expiration dates
- Password-protected links
- Per-item sharing (vs whole wishlist)
- Event-specific share links
- Social media share buttons
- QR code generation

### 8.2 Potential V2 Features

- **Granular permissions**: Share with specific registered users only
- **Event sharing**: Share only items for a specific event (e.g., "Birthday wishlist")
- **Temporary links**: Auto-expire after date or number of views
- **Anonymous claiming**: Allow guests to mark items as "getting this" without login
- **Email invites**: Send share link via email with personalized message

### 8.3 Gift Registry Mode (#48)

Gift Registry Mode is a natural extension of Wishlist Sharing that enables **public claiming** for events like weddings, baby showers, or graduation parties. While this PRD covers read-only sharing, Gift Registry would add:

| Feature | Sharing (V1) | Gift Registry (V2) |
|---------|--------------|-------------------|
| View items | ✅ Anyone with link | ✅ Anyone with link |
| See who claimed | ❌ Hidden | ✅ Visible (no surprise needed) |
| Claim items | ❌ Login required | ✅ Guest can claim with name/email |
| Unclaim items | N/A | ✅ Guest can unclaim |
| Multiple events | ❌ Whole wishlist | ✅ Per-event registry links |

**Implementation notes for Gift Registry:**
- Reuses `ShareLink` model with new `allow_claiming` flag
- New `GuestClaim` model: `(item_id, guest_name, guest_email, created_at)`
- Guest claims don't require login but capture contact info
- Event-specific registry links: `/registry/<event_id>/<token>`
- No surprise protection needed (registry items are public by nature)

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Link enumeration attacks | Privacy breach | UUID v4 tokens + rate limiting |
| Accidental privacy exposure | User trust | Clear UI indicators, confirmation dialogs |
| Confusion about visibility | Support burden | In-app help text, intuitive defaults |
| Performance on popular links | UX degradation | Redis caching, CDN-ready templates |

---

## 10. Appendix

### 10.1 Migration Script Preview

```python
"""Add share_links table

Revision ID: xxxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('share_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(36), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_share_links_token', 'share_links', ['token'])

def downgrade():
    op.drop_table('share_links')
```

### 10.2 Related Documentation

- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Project roadmap
- [LESSONS_LEARNED.md](LESSONS_LEARNED.md) - Technical gotchas
- [CLAUDE.md](../CLAUDE.md) - Development guide
