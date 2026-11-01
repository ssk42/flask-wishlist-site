# responsive-layout EARS Specifications

- [x] **VW-RSP-001**: When any viewer-facing page (items feed, dashboard, events, notifications, item submit/edit forms, my claims, my requests) is rendered at any viewport width, the system shall lay the page out so that no element extends beyond the layout viewport — the document's scroll width shall not exceed the viewport width.
- [x] **VW-RSP-002**: When an item card renders an item whose title is wider than the card, the system shall truncate the title with an ellipsis at the card's edge and shall not widen the card beyond its grid column at any viewport width.
- [x] **VW-RSP-003**: When an item card or modal renders an item image, the system shall contain the image within its card or dialog bounds at every viewport width.
- [x] **VW-RSP-004**: When the viewport is at most 768px wide, the system shall position the floating action button above the mobile tab bar including the device safe-area inset, and shall give page content bottom clearance at least equal to the tab bar's height, so the final card's actions are never covered.
- [x] **VW-RSP-005**: When the viewport is at most 768px wide, the system shall present item-card action controls with a tap target at least 44px tall, uniformly across claim states.
