# Siri / App Intents — Design Spec

**Date:** 2026-07-25
**Status:** Approved
**Scope:** Voice and system-wide access to the wishlist through App Intents, including iOS 27 on-screen awareness.

## Goal

Let someone add to and query the family wishlist without opening the app — by
voice ("Add AirPods to my wishlist"), from the Action button or Shortcuts, and —
on iOS 27 — by referring to what is on screen ("claim this").

## Why App Intents specifically

**SiriKit was deprecated at WWDC 2026.** App Intents is now the only way Siri can
call into a third-party app, so this is not optional polish — it is the supported
integration surface going forward.

## Key finding: no system schema fits a wishlist

Apple's assistant schema domains cover books, browser, camera, documents, files,
journal, mail, photos, presentations, spreadsheets, whiteboard and word
processing. **None covers lists, shopping, or wishlists.**

So we ship **custom `AppIntent`s** rather than conforming to `@AssistantIntent`.
This is not a downgrade: Siri AI discovers and chains custom App Intents.
Conforming to a schema would only buy Apple's canonical phrasing for a domain we
do not belong to, at the cost of contorting our model to fit it.

## What is and isn't reachable by voice

| Goal | Reachable? | Mechanism |
|---|---|---|
| "Add AirPods to my wishlist" | ✅ | Custom intent with a spoken `String` parameter |
| "Add my clipboard to my wishlist" | ✅ | Intent reads the pasteboard, prefills via `/api/v1/metadata` |
| One-tap add from a product page | ✅ | Intent exposed to Shortcuts, wired to Action button / Back Tap / Share sheet |
| "Claim this" while viewing an item **in our app** | ✅ (iOS 27) | On-screen awareness annotations |
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
- **Intent structs** (new, `Wishlist/Intents/`) — `AddWishlistItemIntent`,
  `FindWishlistItemsIntent`, `ClaimItemIntent`, `MyClaimsIntent`, plus
  `WishlistShortcuts: AppShortcutsProvider`.

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
2. `FindWishlistItems` **must not** voice claim status for items the requester
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
3. **Read intents** — `ItemEntity` + `EntityQuery`, `FindWishlistItemsIntent`,
   `MyClaimsIntent`, with the surprise-protection tests.
4. **iOS 27 on-screen awareness** — `.appEntityIdentifier` on `ItemRow` and
   `ItemDetailView`, `.userActivity` on the member list as primary content,
   `ClaimItemIntent` resolving "this". All behind `@available(iOS 27, *)`.

## Constraints

- **Deployment target stays iOS 17.0.** Phases 1–3 use stable iOS 16/17 APIs.
  Phase 4 is additive and availability-gated, so the app keeps running on 17.
- Apple Intelligence features are region-limited; the intents must still work as
  plain Shortcuts actions where Apple Intelligence is unavailable.

## Risk: unverified iOS 27 API surface

Phase 4 rests on APIs that postdate this author's knowledge, and Apple's
documentation pages did not render for automated reading. The names gathered
from WWDC26 session material are `.appEntityIdentifier`, `.userActivity`,
`AppEntityAnnotatable`, `appEntityUIElementProvider`, and
`UICollectionViewAppIntentsDataSource` — **treat these as unconfirmed.** Before
implementing phase 4, verify signatures against the current SDK and WWDC26
sessions 343 ("Explore advanced App Intents features") and 240 ("Build
intelligent Siri experiences with App Schemas").

Phases 1–3 carry no such risk and should not be blocked by phase 4.

## Out of scope

- Conforming to any assistant schema (none fits; revisit if Apple adds a list domain).
- Voice editing or deleting items — higher misrecognition cost than adding, no clear demand.
- Widgets, Live Activities, watchOS, Control Center controls.
- Changing the API, the website, or existing app screens.
