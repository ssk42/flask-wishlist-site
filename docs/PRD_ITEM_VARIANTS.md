# PRD: Item Variants Feature

**Author:** Claude Code
**Created:** 2026-01-04
**Status:** ✅ Implemented
**Related Improvement:** #25 (Item Variants)
**Estimated Effort:** 2 hours

---

## Implementation Progress

| Phase | Task | Status |
|-------|------|--------|
| **Phase 1: Database & Model** | Add fields to Item model | ✅ Complete |
| | Create and run migration (`35d5e463fe94`) | ✅ Complete |
| **Phase 2: Forms** | Update `submit_item.html` with variants row | ✅ Complete |
| | Update `edit_item.html` with variants row | ✅ Complete |
| | Update `items.py` routes | ✅ Complete |
| | Add quantity validation (1-99) | ✅ Complete |
| **Phase 3: Display** | Update `_item_card.html` with badges | ✅ Complete |
| | Update `_item_quick_view.html` | ✅ Complete |
| | Update `my_claims.html` (uses shared partial) | ✅ Complete |
| **Phase 4: Testing** | Unit tests for variant fields (11 tests) | ✅ Complete |
| | All 170 tests passing | ✅ Complete |

**Migration:** `migrations/versions/35d5e463fe94_add_item_variant_fields_size_color_.py`

---

## 1. Overview

### 1.1 Problem Statement

When adding wishlist items, users often need to specify preferences beyond just the product link:

- "I want this sweater in **size Medium**"
- "Please get the **blue** one, not the red"
- "I'd like **2 or 3** of these stocking stuffers"

Currently, users must add these details to the description or comment field, which:
- Makes descriptions cluttered and inconsistent
- Is easy to overlook when viewing items
- Doesn't provide structured data for filtering/display

### 1.2 Proposed Solution

Add dedicated **Size**, **Color**, and **Quantity** fields to wishlist items with:
- Clear, prominent display on item cards
- Easy input on add/edit forms
- Optional fields (not all items need variants)

### 1.3 Success Metrics

| Metric | Target |
|--------|--------|
| Adoption rate | 30% of new items include at least one variant field |
| User satisfaction | No increase in "wrong item purchased" complaints |
| Form completion time | < 5 seconds added to item submission |

---

## 2. User Stories

> **As a wishlist owner**, I want to specify the exact size I need, so gift givers don't have to guess.

> **As a wishlist owner**, I want to indicate my color preference, so I get the variant I actually want.

> **As a wishlist owner**, I want to request multiple quantities of an item, so I can ask for consumables or stocking stuffers.

> **As a gift giver**, I want to see size/color/quantity at a glance, so I don't have to search through descriptions or follow links.

---

## 3. Functional Requirements

### 3.1 New Fields

| Field | Type | Constraints | Examples |
|-------|------|-------------|----------|
| `size` | String(50) | Optional, freeform | "Medium", "10.5", "XL", "32x30", "Queen" |
| `color` | String(50) | Optional, freeform | "Blue", "Navy Blue", "Rose Gold", "Pattern: Floral" |
| `quantity` | Integer | Optional, min=1, max=99 | 1, 2, 5 |

**Design Decision: Freeform vs. Dropdowns**

Freeform text was chosen over predefined dropdowns because:
- Sizes vary wildly by product type (clothing S-XL, shoes 6-13, bedding Twin-King, etc.)
- Colors include custom names ("Midnight Blue", "Sage", "Rose Gold")
- Users can include additional context ("Size 8 Wide", "Any neutral color")

### 3.2 Display Requirements

#### 3.2.1 Item Card Display

Variants should appear prominently below the price, using pill badges:

```
┌─────────────────────────────────────────┐
│ [Image]                                 │
│                                         │
│ Cozy Knit Sweater                       │
│ Clothing                                │
│ $49.99                                  │
│                                         │
│ [Size: Medium] [Color: Navy] [Qty: 1]   │  <-- New variant badges
│                                         │
│ [Claim] [View] [Link]                   │
└─────────────────────────────────────────┘
```

#### 3.2.2 Badge Styling

| Badge | Icon | Color |
|-------|------|-------|
| Size | `bi-rulers` | `bg-secondary` |
| Color | `bi-palette` | `bg-secondary` |
| Quantity | `bi-stack` | `bg-info` (only if qty > 1) |

- Badges only appear if field has a value
- Quantity badge only appears if quantity > 1 (assume 1 is default)

### 3.3 Form Requirements

#### 3.3.1 Submit Item Form

Add a new "Variants" row after the Price/Priority/Status/Category row:

```
┌─────────────────────────────────────────────────────────┐
│ Variants (optional)                                     │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│ │ Size        │ │ Color       │ │ Quantity    │        │
│ │ [Medium   ] │ │ [Navy     ] │ │ [1        ] │        │
│ └─────────────┘ └─────────────┘ └─────────────┘        │
│ Specify size, color, or quantity if it matters.        │
└─────────────────────────────────────────────────────────┘
```

- All three fields in one row (col-md-4 each)
- Placeholder text hints: "M, L, XL...", "Blue, Red...", "1"
- Quantity defaults to empty (displays as 1 implicitly)

#### 3.3.2 Edit Item Form

Same layout as submit form, pre-populated with existing values.

### 3.4 Quick View Modal

Update `_item_quick_view.html` to show variant details in the details section.

### 3.5 My Claims Page

Show variant info on claimed items so gift-givers remember what to buy.

### 3.6 Export

Include Size, Color, Quantity columns in Excel export.

---

## 4. Technical Design

### 4.1 Database Changes

#### 4.1.1 Migration

```python
"""Add variant fields to Item model

Revision ID: xxxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('item', sa.Column('size', sa.String(50), nullable=True))
    op.add_column('item', sa.Column('color', sa.String(50), nullable=True))
    op.add_column('item', sa.Column('quantity', sa.Integer, nullable=True))

def downgrade():
    op.drop_column('item', 'size')
    op.drop_column('item', 'color')
    op.drop_column('item', 'quantity')
```

#### 4.1.2 Model Update

```python
# models.py - Item class
size = db.Column(db.String(50), nullable=True)
color = db.Column(db.String(50), nullable=True)
quantity = db.Column(db.Integer, nullable=True)
```

### 4.2 Route Changes

#### 4.2.1 Items Blueprint

**`submit_item` route** (`blueprints/items.py`):
- Add `size`, `color`, `quantity` to form processing
- Validate quantity is positive integer if provided

**`edit_item` route**:
- Same changes as submit_item
- Pass existing values to template

### 4.3 Template Changes

| Template | Changes |
|----------|---------|
| `submit_item.html` | Add variants row with 3 fields |
| `edit_item.html` | Add variants row, pre-populate values |
| `partials/_item_card.html` | Add variant badges below price |
| `partials/_item_quick_view.html` | Add variants to details section |
| `my_claims.html` | Show variants on claimed items |

### 4.4 Validation Rules

| Field | Validation |
|-------|------------|
| `size` | Max 50 chars, strip whitespace |
| `color` | Max 50 chars, strip whitespace |
| `quantity` | Integer 1-99, or None |

### 4.5 Autofill Enhancement (Optional V2)

The existing URL autofill feature (`/api/fetch-metadata`) could be extended to extract variant info from product pages. This is out of scope for V1 but noted for future consideration.

---

## 5. User Interface

### 5.1 Item Card with Variants

```
┌─────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────┐ │
│ │                    [Product Image]                  │ │
│ │  [Your Item]                            [High]      │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ Nike Air Pegasus Running Shoes                          │
│ 🏷️ Footwear                                             │
│ $129.99 (as of Jan 3)                                   │
│                                                         │
│ 📏 Size 10.5  🎨 Black/White  📦 ×1                     │
│                                                         │
│ ───────────────────────────────────────────────────── │
│ [Edit]                              [Delete]            │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Submit Form with Variants

```
┌─────────────────────────────────────────────────────────┐
│ 🎁 Add a new wishlist item                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Description *                    Link                   │
│ ┌────────────────────────┐      ┌────────────────────┐ │
│ │ Nike Running Shoes     │      │ https://nike.com   │ │
│ └────────────────────────┘      └────────────────────┘ │
│                                                         │
│ Price      Priority    Status      Category             │
│ ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐        │
│ │ $129   │ │ High ▼ │ │ Avail ▼ │ │ Footwear │        │
│ └────────┘ └────────┘ └─────────┘ └──────────┘        │
│                                                         │
│ Variants (optional)                                     │
│ ┌────────────┐ ┌────────────┐ ┌────────────┐          │
│ │ Size       │ │ Color      │ │ Quantity   │          │
│ │ 10.5       │ │ Black      │ │ 1          │          │
│ └────────────┘ └────────────┘ └────────────┘          │
│ Specify size, color, or quantity if it matters.        │
│                                                         │
│                           [Cancel]  [Save item]         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Plan

### Phase 1: Database & Model (15 min)
1. Add fields to `Item` model in `models.py`
2. Create and run migration
3. Verify fields in database

### Phase 2: Forms (30 min)
1. Update `submit_item.html` with variants row
2. Update `edit_item.html` with variants row
3. Update `items.py` routes to handle new fields
4. Add validation for quantity

### Phase 3: Display (45 min)
1. Update `_item_card.html` with variant badges
2. Update `_item_quick_view.html` with variants
3. Update `my_claims.html` to show variants
4. Style badges consistently

### Phase 4: Testing (30 min)
1. Unit tests for variant field handling
2. Browser tests for add/edit with variants
3. Verify export includes new columns

**Total Estimated Effort:** ~2 hours

---

## 7. Testing Requirements

### 7.1 Unit Tests

| Test Case | Expected Result |
|-----------|-----------------|
| Submit item with all variants | Item created with size/color/quantity |
| Submit item without variants | Item created, variant fields null |
| Edit item to add variants | Item updated with new values |
| Edit item to remove variants | Item updated, fields set to null |
| Quantity validation (negative) | Form rejects, shows error |
| Quantity validation (> 99) | Form rejects, shows error |
| Size/color max length | Truncated to 50 chars |

### 7.2 Browser Tests

| Flow | Steps |
|------|-------|
| Add item with variants | Fill form with size/color/qty → Save → Verify badges visible |
| Edit item variants | Edit existing item → Change size → Save → Verify updated |
| View claimed item | Claim item with variants → My Claims → Verify variants shown |

---

## 8. Future Considerations

### 8.1 Out of Scope (V1)

- Autofill variants from product URLs
- Variant-specific pricing (different sizes = different prices)
- Multiple variant combinations per item (size M AND size L)
- Structured size dropdowns (S/M/L/XL picker)
- Color swatches/pickers
- Filtering items by variant fields

### 8.2 Potential V2 Features

- **Smart autofill**: Parse variant options from Amazon/Target product pages
- **Common sizes dropdown**: Optional dropdown for standard clothing sizes
- **Variant groups**: "I want this in either Blue or Green" (alternative options)
- **Partial fulfillment**: Track when 2 of 3 requested quantity have been claimed

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users ignore new fields | Low adoption | Place visually near price, add helper text |
| Freeform creates inconsistency | Messy data | Accept tradeoff for flexibility |
| Form feels cluttered | UX friction | Group in single row, label "optional" |
| Export breaks existing workflows | User frustration | Add columns at end, don't change existing |

---

## 10. Appendix

### 10.1 Existing `comment` Field

The Item model already has a `comment` field (String(100)) used for personal notes. This is separate from the Comment model used for discussions between gift-givers.

The `comment` field is NOT being replaced - it serves a different purpose (notes like "for the kitchen" or "any edition is fine"). Variants are for specific product attributes.

### 10.2 Badge HTML Example

```html
{% if item.size %}
<span class="badge bg-secondary bg-opacity-75 me-1">
    <i class="bi bi-rulers me-1"></i>{{ item.size }}
</span>
{% endif %}
{% if item.color %}
<span class="badge bg-secondary bg-opacity-75 me-1">
    <i class="bi bi-palette me-1"></i>{{ item.color }}
</span>
{% endif %}
{% if item.quantity and item.quantity > 1 %}
<span class="badge bg-info bg-opacity-75">
    <i class="bi bi-stack me-1"></i>×{{ item.quantity }}
</span>
{% endif %}
```

### 10.3 Related Documentation

- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Project roadmap
- [models.py](../models.py) - Database models
- [submit_item.html](../templates/submit_item.html) - Add item form
