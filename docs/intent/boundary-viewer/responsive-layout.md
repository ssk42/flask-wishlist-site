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
A flex item's automatic minimum size is its content's min-content width,
and min-content propagates through every flex ancestor in turn — breaking
one link leaves the outer links to re-form the chain. Two content classes
feed it: item titles render with `text-truncate` (`white-space: nowrap`),
so a title's min-content is its full unwrapped text (measured at 570px
for a real catalogue title); and a product image is a replaced element
whose min-content contribution is its intrinsic width (measured at 894px
for a real catalogue photo), because its percentage width resolves as
automatic for intrinsic sizing. The chain from either source runs through
every flex box between the content and the page:

- the card is a flex column, and the card body is one of its flex items;
- the Bootstrap grid column is a flex item of the row (`flex-shrink: 0`);
- the main content region is the growing flex item of the sidebar shell.

Unbroken, the minimum reaches the page unchanged: on a 390px phone
viewport the items page laid out 668px wide behind a long title, and at a
606px window a wide product photo laid it out 992px wide — the card
measured 928px inside a 952px column — while the visual viewport stayed
put and cards extended past the screen edge. The repair breaks the chain
at every flex item on the path: the shell's main content, every grid
column (`.row > *`), direct flex children of a card, and children of flex
rows inside a card may all shrink below their content's min-content
(`min-width: 0`). Their sizes then come from the layout — the shell's
flex basis, the column's grid width, the card's column — never from the
content. Truncation does what it was always meant to do (the title
ellipsizes at the card's edge instead of stretching the card), and the
image's cover frame crops the photo to the card. Where content already
fits, nothing changes; desktop rendering is unaffected.

## Components
- **Stylesheet (`static/css/main.css`)**: the single implementation site.
  It carries the min-content chain rules — the layout-ancestor shrink
  rules for the shell's main content and the grid columns, and the card
  flex-child shrink rule — the image containment rule, and the
  small-viewport block that handles the floating action button, the
  mobile tab bar, content bottom clearance, and card-action tap targets.
- **Templates**: the base template already declares the device
  viewport; cards and grids already use fluid Bootstrap classes. The
  sizing defects were stylesheet rules, not structure. Card image
  elements carry the loading contract directly: lazy loading and
  asynchronous decoding attributes on the item-card and quick-view
  images.

## Small-viewport rules (≤768px)
- The mobile tab bar pads for the device safe-area inset, and the
  floating action button and the main content's bottom clearance are
  computed from the same inset, so the button never covers the final
  card's actions and the tab bar never crowds the home indicator.
- Item-card action controls present a tap target at least 44px tall.
  The enlargement is uniform across claim states, preserving the
  equal-footprint invariant of GIV-CLM-020.

## Renderer load at small viewports
Fitting the viewport is necessary but not sufficient: the page must also
stay within the renderer process's compositing and decode budget, or a
mobile browser kills and reloads it ("A problem repeatedly occurred").
The dominant cost on the items feed is the card's backdrop-filter blur —
each blurred card is an offscreen compositing pass over the card's full
area, re-rendered as the page scrolls. The feed renders every unarchived
item (39 cards on the production catalogue), each carrying a 12–16px
blur: some 17 million square pixels of composited backdrop. At ≤768px
cards therefore drop the backdrop filter entirely and fall back to the
solid surface color; the glass background is already 85% opaque, so the
visual change is slight, and desktop keeps the full glass treatment.
Card images are remote photos at full catalogue resolution (1500×1500
samples measured). They load lazily — only near-viewport images are
fetched and decoded — and decode asynchronously, so the decode load
never lands as one burst on the renderer's critical path.

## Decisions & Alternatives
| Decision | Alternative Considered | Rationale |
|----------|------------------------|-----------|
| Break the min-content chain with `min-width: 0` on card flex children | Shorten titles server-side; drop `text-truncate`; set `overflow: hidden` on the page | Server-side shortening changes displayed content and desktop rendering. Dropping truncation loses the ellipsis design. Page-level overflow clipping hides the symptom while leaving cards internally mis-sized, and clips shadows, dropdowns, and modal edges. The flex minimum-size rule is the standard repair and is a no-op wherever content already fits. |
| Host the specs in a new `responsive-layout` leaf under `boundary-viewer` | Extend item-claiming's spec file (GIV-CLM-022+) | The contract spans every viewer page — items feed, dashboard, events, notifications, forms, claims/requests, modals — not the giver claim flow. boundary-viewer is the HLD's presentation layer; item-claiming keeps the card's height-across-states rules, this node owns width-across-viewports. |
| Enlarge tap targets only inside the ≤768px media query | Enlarge card buttons at all widths | Desktop rendering must not change; pointer precision on desktop makes the compact pills appropriate there. |
| Keep the card image's fixed-height cover frame | Switch the frame to an aspect-ratio box | The 200px cover frame already yields uniform cards; changing its geometry would alter desktop rendering for no responsive benefit. Containment, not the frame, was the defect. |
| Break the min-content chain at every flex ancestor — shell content and grid columns, not only inside the card | Cap the card media wrapper; clip overflow on the grid or the page | Min-content propagates through each flex item in turn, so an innermost-only break leaves the column and the shell to re-form the chain around any wide content (a photo's intrinsic width widens the column exactly as a nowrap title widens the card). Clipping hides the symptom while leaving the layout mis-sized, and clips shadows, dropdowns, and modal edges. Ancestor `min-width: 0` is a no-op wherever content already fits, and grid columns take their width from their column classes either way. |
| Drop the card backdrop filter entirely at ≤768px, with a solid surface-color fallback | Reduce the blur radius; blur only the first screenful of cards | A smaller radius still pays a full offscreen compositing pass per card, and which cards are "first" changes with scrolling and filtering. The count of blurred surfaces, not the radius, is the load driver — zero is the only count that scales as the catalogue grows. The glass background is already 85% opaque, so the solid fallback is visually near-identical. |

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
- **Item image**: a replaced element, so its intrinsic width is a
  min-content source in its own right — a real 894px-wide catalogue photo
  widened its column and the page at a 606px window even with every
  intra-card element already at `min-width: 0`, because the column and
  the shell still propagated it. The ancestor links of the chain (grid
  columns, main content) break that propagation; the cover frame then
  crops the photo to the card, and the `max-width: 100%` rule for images
  in the main content and modals is kept as containment hygiene.
- **Quick-view and split modals**: Bootstrap dialog sizing is fluid below
  576px; the quick-view image uses a ratio box with `img-fluid`; the
  split modal's thumbnail is a fixed 60px. No changes needed.
- **Forms (submit/edit), events, notifications, my-claims, my-requests**:
  standard wrapping Bootstrap rows; measured 390/390 pre-fix. They are
  covered by the same no-overflow spec and re-measured after the fix.
- **Filter panel**: its selects measured as victims (sized by the
  expanded layout), not causes; hiding it did not change the layout
  width.
- **Renderer load**: the entrance animations are finite one-shot
  effects and the image-loading shimmer is transient; neither composites
  continuously. The modal backdrop is a flat dim layer, not a blur. The
  persistent loads are the card backdrop filters (39 of 39 cards
  measured blurred at phone width) and full-resolution image decodes;
  both are addressed by the small-viewport rules above.

## Requirement traceability
Behavior is specified by VW-RSP-001 through VW-RSP-006 in
[the responsive-layout requirements](responsive-layout/responsive-layout-specs.md).
