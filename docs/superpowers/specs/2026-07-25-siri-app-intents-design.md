# Siri / App Intents — Design Spec

**Date:** 2026-07-25
**Status:** Approved
**Scope:** Voice and system-wide access to the wishlist through App Intents, including iOS 27 on-screen awareness.

## Goal

Let someone add to and query the family wishlist without opening the app — by
voice, from the Action button or Shortcuts, and by referring to what is on
screen ("claim this").

> **Corrected after implementation.** This spec originally promised the single
> utterance "Add AirPods to my wishlist". That is **not achievable**: an
> `AppShortcut` phrase can only interpolate `AppEntity`/`AppEnum` parameters, and
> the item name is deliberately free text. Adding by voice is a two-turn
> exchange — "Add to my Wishlist" → *"What should I add?"* Claiming stays
> one-shot ("Claim the blanket in Wishlist") because its parameter IS an
> `AppEntity`. See `ios/README.md` for the shipped behaviour.

## Why App Intents specifically

**SiriKit was deprecated at WWDC 2026.** App Intents is now the only way Siri can
call into a third-party app, so this is not optional polish — it is the supported
integration surface going forward.

## Schemas: which we adopt, and which we deliberately refuse

Verified against Apple's current documentation (2026). The full domain list:

- **Primary** (Apple Intelligence + Siri): audio, calendar, camera, clock, files,
  mail, maps, messages, notes, phone, photos, **reminders**,
  **system and in-app search**
- **Single-purpose**: assistant, visual intelligence
- **Shortcuts-only** (no Apple Intelligence/Siri discoverability): books, browser,
  journaling, presentation, reader, spreadsheet, whiteboard, word processor

Schemas are applied with `@AppIntent(schema:)`, `@AppEntity(schema:)` and
`@AppEnum(schema:)`. Xcode generates template implementations when you type the
domain prefix (`system_`, `reminders_`) and pick from the suggestion list.

### Adopt: `.system` (search and open)

The `.system` domain is explicitly **not** category-specific — "any app that
enables searching or opening content can adopt these schemas". Two schemas, both
a genuine fit:

| Schema | Purpose | Availability |
|---|---|---|
| `.system.searchInApp` | Search within the app | iOS 27+ |
| `.system.open` | Open a specific item | iOS 27+ |

Adopting these gives the read side real Apple Intelligence discoverability —
"find the cashmere blanket in Wishlist" — which custom intents alone would not.

**Availability, read from `AppIntents.swiftinterface` in the Xcode-beta SDK
rather than from memory:**

- `.system.search` (no `InApp`) is **deprecated**: *"Use .system.searchInApp
  instead"*. Do not use it.
- `.system.searchInApp` and `.system.open` are `@available(anyAppleOS 27.0, *)`.
- The `@AppIntent(schema:)` macro itself is iOS 18+; the `.system` domain is 18+.
- The underlying protocols are much older — `ShowInAppSearchResultsIntent` is
  iOS 17.2 and `OpenIntent` is iOS 16.0 (and supplies a default `perform()`).
  Conforming to those directly would reach the app's iOS 17 floor but forgoes
  schema registration.

**Decision:** use the iOS 27 schemas behind `@available(iOS 27, *)`. The read
intents therefore do not exist below iOS 27; the add and claim intents, which
are custom and ungated, still work on the iOS 17 floor. This was chosen over
raw-protocol conformance because Apple Intelligence discoverability is the whole
reason for adopting a schema, and over the deprecated `.system.search` because
building on an already-deprecated API is a known future break.

### Refuse: `.reminders`

The reminders domain is the only one offering "create an item inside a list"
(`createList`, `createReminder`, `createSection`, `deleteReminders`,
`updateReminder`, `updateGroup`, `updateList`, `updateSection`, with `list`,
`reminder`, `section`, `group` and `locationTrigger` entities). On paper a
wishlist looks like a list of items, so it is worth saying explicitly why we do
not use it:

1. **It would hijack real reminders.** Conforming to `.reminders.createReminder`
   enters Wishlist into the pool of apps Siri may pick for "create a reminder".
   Someone asking for a grocery reminder could silently get a wishlist item.
   That is a worse failure than lacking the integration.
2. **The shape does not fit.** Reminder schemas carry due dates, completion
   state, location triggers, sections and groups. A gift has a price, a link, a
   priority and a claim state — modelling it as a reminder means either
   discarding our fields or faking theirs.
3. **"Mark as completed" is not "claim".** `updateReminder`'s semantics would
   invite Siri to phrase claiming as completion, which misdescribes the one
   behaviour this app most needs to get right.

### Therefore: custom intents for add and claim

No schema covers "add an item to a wishlist" except the reminders one we are
refusing, so `AddWishlistItem` and `ClaimItem` are **custom** `AppIntent`s
surfaced through `AppShortcutsProvider`. Post-SiriKit-deprecation, custom App
Intents remain a first-class Siri surface — they simply lack Apple's canonical
cross-app phrasing, which for a bespoke concept like a family wishlist does not
exist anyway.

## What is and isn't reachable by voice

| Goal | Reachable? | Mechanism |
|---|---|---|
| "Add AirPods to my wishlist" | ⚠️ two-turn | A `String` parameter cannot be interpolated into a phrase; Siri prompts for the name |
| "Add my clipboard to my wishlist" | ✅ | Intent reads the pasteboard, prefills via `/api/v1/metadata` |
| One-tap add from a product page | ✅ | Intent exposed to Shortcuts, wired to Action button / Back Tap / Share sheet |
| "Claim this" while viewing an item **in our app** | ✅ (iOS 18.2) | On-screen awareness annotations |
| "Add this" while browsing **Safari** | ❌ | No API hands a third-party intent another app's page. The Share Extension (already shipped) covers this case. |

The last row is the one users will expect to work. On-screen awareness surfaces
*our own* annotated entities — it is not cross-app content handoff.

## Architecture

Logic lives in `WishlistKit`; the intent structs stay thin and live in the app
target, because `AppShortcutsProvider` must be in the app target.

```
Siri / Shortcuts / Action button
        ↓
AppIntent structs           (app target — thin, no business logic)
        ↓
IntentService               (WishlistKit — testable, offline-stubbable)
        ↓
APIClient  →  /api/v1       (existing, unchanged)
```

- **`IntentService`** (new, `WishlistKit/Intents/IntentService.swift`) — one
  method per intent action. Owns auth checks, error translation, and the
  surprise-protection rules. This is where the tests go.
- **`ItemEntity`** (new, `WishlistKit/Intents/ItemEntity.swift`) — `AppEntity`
  wrapper over `Item` with an `EntityQuery`. Carries `id`, `description`,
  `price`, owner name, and an **optional** `status`.
- **Intent structs** (new, `Wishlist/Intents/`), plus
  `WishlistShortcuts: AppShortcutsProvider`:

| Intent | Schema | Example phrase |
|---|---|---|
| `AddWishlistItemIntent` | custom | "Add AirPods to my wishlist" |
| `SearchWishlistIntent` | `@AppIntent(schema: .system.searchInApp)`, iOS 27+ | "Find the cashmere blanket in Wishlist" |
| `OpenWishlistItemIntent` | `@AppIntent(schema: .system.open)`, iOS 27+ | "Open the blanket in Wishlist" |
| `ClaimItemIntent` | custom | "Claim this" / "Claim the blanket" |
| `MyClaimsIntent` | custom | "What have I claimed?" |

The two `.system` conformances are what give the read side genuine Apple
Intelligence discoverability; the rest ride on `AppShortcutsProvider` phrases.

Nothing in the existing app, API, or `APIClient` changes. This is additive.

## Authentication

Intents reuse `KeychainTokenStore` on the shared access group — the same token
the app writes at login. Consequences worth stating plainly:

- **This feature is device-only.** Unsigned simulator builds cannot read the
  shared Keychain group, so intents will always report "not signed in" there.
  Same constraint as push and the Share Extension.
- **No token → a clear spoken error**, never a crash and never a silent no-op:
  "Open Wishlist and log in first." `IntentService` checks this before any
  network call.

## Surprise protection

This is the sharpest edge in the feature. A read intent is a *new channel* for
leaking exactly what the API deliberately hides, and Siri speaks its results out
loud, possibly to a room.

Rules, enforced in `IntentService` and `ItemEntity`:

1. `ItemEntity.status` is **optional** and absent for the viewer's own items,
   mirroring `serialize_item`. Never default a missing status.
2. `SearchWishlistIntent` **must not** voice claim status for items the requester
   owns — for their own list it reports items only.
3. `ClaimItem` must refuse an item the requester owns, with a spoken reason
   (the API already returns `409 own_item`; the intent translates it).

These get their own tests. Inheriting the API's correctness is not sufficient,
because the leak here would be in *our* phrasing, not the payload.

## Error handling

| Condition | Behaviour |
|---|---|
| No token | Spoken: "Open Wishlist and log in first." No network call. |
| `401` mid-flight | Same message — the token was revoked or expired. |
| `409 own_item` / `not_available` | Speak the existing friendly text already used in `MemberItemsViewModel`. |
| `400` validation | Speak the first server message. |
| Network failure | "Couldn't reach the wishlist. Try again." |
| Empty description | Ask Siri to prompt for the value (`@Parameter` requiring a value) rather than failing. |

`ClaimItem` requests confirmation before acting. Claiming changes what other
people see and is hard to notice if wrong, so a misheard item name must not
silently commit.

## Testing

- **`IntentService`**: real unit tests against the existing `StubURLProtocol` —
  auth-missing path, each error translation, and the three surprise-protection
  rules above.
- **`ItemEntity`**: decoding and the optional-status invariant.
- **Intent structs**: `perform()` exercised with an injected fake service; they
  are thin by design so there is little to test beyond parameter wiring.
- **Manual, on device**: Siri phrase matching, the Shortcuts entry, Action-button
  wiring. An **iOS 27 simulator runtime is installed** (`27.0 24A5390f`) so
  annotations can be smoke-tested, but Siri and Apple Intelligence behaviour
  cannot be asserted in CI and must not be claimed as verified from a build alone.

## Phasing

Each phase is independently shippable and useful.

1. **Add by voice** — `IntentService.addItem`, `AddWishlistItemIntent`,
   `WishlistShortcuts` with spoken-name and clipboard phrases. iOS 17 compatible.
2. **Shortcuts / Action button** — optional `url` parameter on the same intent,
   `/api/v1/metadata` prefill, and an `AppShortcut` shaped for a URL input.
3. **Read intents** — `ItemEntity` + `EntityQuery`, `SearchWishlistIntent`
   (`.system.searchInApp`), `OpenWishlistItemIntent` (`.system.open`) and
   `MyClaimsIntent`, with the surprise-protection tests. The two schema
   conformances are iOS 27-gated; `ItemEntity` and `MyClaimsIntent` are not. Schema conformance is
   verifiable at build time: the macros fail to compile if the intent's shape
   does not match the schema, so a mistake here is caught by CI, not by Siri.
4. **On-screen awareness** — as built: `NSUserActivity.appEntityIdentifier` on
   `ItemDetailView` only, behind `@available(iOS 18.2, *)`. There is no SwiftUI
   `.appEntityIdentifier` view modifier, and `NSUserActivity` is screen-level, so
   the per-row annotation this section originally described is not a thing.

## Constraints

- **Deployment target stays iOS 17.0.** Phases 1–2 use stable iOS 16/17 APIs.
  The two schema conformances in phase 3 and all of phase 4 are
  `@available(iOS 27, *)`-gated, so the app keeps running on 17 without them.
- Apple Intelligence features are region-limited; the intents must still work as
  plain Shortcuts actions where Apple Intelligence is unavailable.

## Risk: unverified iOS 27 API surface

Phase 4 rests on APIs that postdate this author's knowledge, and Apple's
documentation pages did not render for automated reading. **Resolved by reading the SDK.** Of the names gathered from WWDC26 session
material: `AppEntityAnnotatable` and `appEntityIdentifier` are real, but live on
`NSUserActivity` at **iOS 18.2**, not 27, and are reached via SwiftUI's existing
`.userActivity(_:isActive:_:)`. `appEntityUIElementProvider` and
`UICollectionViewAppIntentsDataSource` **do not exist** under those names — they
are UIKit-side concepts this SwiftUI app never needed. Before
implementing phase 4, verify signatures against the current SDK and WWDC26
sessions 343 ("Explore advanced App Intents features") and 240 ("Build
intelligent Siri experiences with App Schemas").

Phases 1–3 carry no such risk and should not be blocked by phase 4. The
`.system.searchInApp` / `.system.open` schemas used in phase 3 were read directly
from the SDK's `AppIntents.swiftinterface` and their conformance is
compiler-checked, so a wrong shape fails the build rather than reaching a user.

## Out of scope

- Conforming to any assistant schema (none fits; revisit if Apple adds a list domain).
- Voice editing or deleting items — higher misrecognition cost than adding, no clear demand.
- Widgets, Live Activities, watchOS, Control Center controls.
- Changing the API, the website, or existing app screens.
