# responsive-layout LLD

## Core Concept
The responsive-layout segment owns the presentation contract that every
viewer-facing page fits the viewport it is rendered on. Pages are laid out
with Bootstrap's grid inside a flex shell (sidebar + main content) and item
cards that are themselves flex columns. The segment's guarantee is that no
content — however long an item title, description, or image — can widen a
page beyond its layout viewport, and that on phone-sized viewports the
primary actions remain reachable and tappable. It complements
item-claiming's card geometry rules (GIV-CLM-020), which keep a card's
height stable across claim states; this segment keeps every card and page
within its width across viewport sizes.

## The flex minimum-size chain
A flex item's automatic minimum size is its content's min-content width.
Item titles render with `text-truncate` (`white-space: nowrap`), so a
title's min-content is its full unwrapped text — measured at 570px for a
real catalogue title. The card is a flex column, the card body is one of
its flex items, and the Bootstrap grid column is a non-shrinking flex item
of the row, so that minimum propagates unchanged to the page: on a 390px
phone viewport the items page laid out 668px wide, the visual viewport
stayed 390px, and cards (with their images) extended past the screen edge.
The repair breaks the chain at the flex items themselves: direct flex
children of a card, and children of flex rows inside a card, may shrink
below their content's min-content (`min-width: 0`). Truncation then does
what it was always meant to do — the title ellipsizes at the card's edge
instead of stretching the card. Where content already fits, nothing
changes; desktop rendering is unaffected.

## Components
- **Stylesheet (`static/css/main.css`)**: the single implementation site.
  It carries the card flex-child shrink rule, the image containment rule,
  and the small-viewport block that handles the floating action button,
  the mobile tab bar, content bottom clearance, and card-action tap
  targets.
- **Templates**: unchanged markup. The base template already declares the
  device viewport; cards and grids already use fluid Bootstrap classes.
  The defects were sizing rules, not structure.

## Small-viewport rules (≤768px)
- The mobile tab bar pads for the device safe-area inset, and the
  floating action button and the main content's bottom clearance are
  computed from the same inset, so the button never covers the final
  card's actions and the tab bar never crowds the home indicator.
- Item-card action controls present a tap target at least 44px tall.
  The enlargement is uniform across claim states, preserving the
  equal-footprint invariant of GIV-CLM-020.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| Break the min-content chain with `min-width: 0` on card flex children | Shorten titles server-side; drop `text-truncate`; set `overflow: hidden` on the page | Server-side shortening changes displayed content and desktop rendering. Dropping truncation loses the ellipsis design. Page-level overflow clipping hides the symptom while leaving cards internally mis-sized, and clips shadows, dropdowns, and modal edges. The flex minimum-size rule is the standard repair and is a no-op wherever content already fits. |
| Host the specs in a new `responsive-layout` leaf under `boundary-viewer` | Extend item-claiming's spec file (GIV-CLM-022+) | The contract spans every viewer page — items feed, dashboard, events, notifications, forms, claims/requests, modals — not the giver claim flow. boundary-viewer is the HLD's presentation layer; item-claiming keeps the card's height-across-states rules, this node owns width-across-viewports. |
| Enlarge tap targets only inside the ≤768px media query | Enlarge card buttons at all widths | Desktop rendering must not change; pointer precision on desktop makes the compact pills appropriate there. |
| Keep the card image's fixed-height cover frame | Switch the frame to an aspect-ratio box | The 200px cover frame already yields uniform cards; changing its geometry would alter desktop rendering for no responsive benefit. Containment, not the frame, was the defect. |

## Edge audit
Surfaces checked for the same failure class (a flex/grid ancestor that can
be widened by nowrap or replaced content, fixed widths, or missing
containment), by code inspection and by live measurement at 390px before
the fix:

- **Dashboard**: shares the card trap — `_dashboard_item_card.html` is the
  same flex-column card with a truncating title inside a flex header row.
  Covered by the same stylesheet rule (its header row is a flex row inside
  a card). Measured 390/390 pre-fix only because its current titles are
  short.
- **Item image**: contained by its frame in every measurement; blocking
  all product images did not change the items page's 668px layout, which
  rules images out as the overflow source. A `max-width: 100%` rule for
  images in the main content and modals is kept as containment hygiene.
- **Quick-view and split modals**: Bootstrap dialog sizing is fluid below
  576px; the quick-view image uses a ratio box with `img-fluid`; the
  split modal's thumbnail is a fixed 60px. No changes needed.
- **Forms (submit/edit), events, notifications, my-claims, my-requests**:
  standard wrapping Bootstrap rows; measured 390/390 pre-fix. They are
  covered by the same no-overflow spec and re-measured after the fix.
- **Filter panel**: its selects measured as victims (sized by the
  expanded layout), not causes; hiding it did not change the layout
  width.

## Requirement traceability
Behavior is specified by VW-RSP-001 through VW-RSP-005 in
[the responsive-layout requirements](responsive-layout/responsive-layout-specs.md).
