# owner-visibility EARS Specifications

- [x] **OWN-VIS-001**: While viewing the items list or dashboard, if the item
  belongs to the current user, the system shall hide the item's true claim status
  and instead display a "Your Item" badge; the quick-view modal shall also hide
  the claim status (rendering no status/action block for the owner).
- [x] **OWN-VIS-002**: While viewing the items list or dashboard, if the item belongs to the current user, the system shall hide the "Last updated by" and "Claimed by" information.
- [x] **OWN-VIS-003**: While viewing the items list or dashboard, if an item belongs to the current user and is a split gift, the system shall hide the split progress and contributions, displaying the item as normally "Available".
- [x] **OWN-VIS-004**: While viewing the item details, if the item belongs to the current user, the system shall completely hide the comments section.
- [x] **OWN-VIS-005**: While viewing the items list summary ("At a Glance" table), the system shall exclude any items owned by the current user from the claimed/purchased statistical totals.
- [x] **OWN-VIS-006**: While editing an item, if the item belongs to the current user, the system shall hide the status dropdown to prevent them from seeing or changing the claim status.
