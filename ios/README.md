# Wishlist for iOS

Native SwiftUI client for the family wishlist, talking to the Flask
[`/api/v1`](../docs/API_V1.md) JSON API.

## Layout

| Target | What it is |
|---|---|
| `WishlistKit` | Framework: models, `APIClient`, Keychain token store, view models. Everything testable lives here. |
| `Wishlist` | The app: login + four tabs (Family, My List, Claims, Activity). |
| `ShareExtension` | "Add to Wishlist" from Safari's share sheet. |
| `WishlistKitTests` | Unit tests (65), all offline via a stubbed `URLProtocol`. |

`ios/project.yml` is the source of truth — the `.xcodeproj` is generated and
git-ignored.

## Prerequisites

```bash
brew install xcodegen
```

Xcode with an iOS simulator runtime. Note this project was built against an
Xcode **beta**; if `xcodebuild` reports the iOS platform is missing, either
`sudo xcodebuild -downloadPlatform iOS` or point at the beta for one command:

```bash
export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
```

## Generate the project

**The `--project-root .` flag is required.** Without it, XcodeGen resolves the
`ios/`-prefixed `sources:` paths against `ios/` and looks for `ios/ios/…`.

```bash
xcodegen generate --spec ios/project.yml --project-root .
```

Re-run it whenever you add or remove a source file.

## Build and test

```bash
xcodebuild -project ios/Wishlist.xcodeproj -scheme WishlistKit \
  -destination 'platform=iOS Simulator,name=iPhone 17' test
```

```bash
xcodebuild -project ios/Wishlist.xcodeproj -scheme Wishlist \
  -destination 'platform=iOS Simulator,name=iPhone 17' build
```

Code signing is disabled **for the simulator only**
(`CODE_SIGNING_ALLOWED[sdk=iphonesimulator*]=NO`), so simulator builds and CI need
no certificates. Device builds sign normally with `DEVELOPMENT_TEAM`.

## Running on a physical iPhone

Needed for the two things the simulator can't do: APNs device-token registration
and the Share Extension's authenticated save (both require the shared Keychain
access group, which only a signed build gets).

1. In the Apple Developer portal, register App IDs for `com.reitz.wishlist` and
   `com.reitz.wishlist.ShareExtension`, and enable the **Push Notifications**
   capability on the app's App ID. APNs rejects a topic for an unregistered
   bundle ID.
2. Regenerate and open the project, plug in the iPhone, select it as the
   destination, and run. Signing is already configured — `DEVELOPMENT_TEAM` is
   set in `project.yml` and the `aps-environment` / keychain-group entitlements
   are in place.
3. Log in on the device, then confirm a token reached the server:

```bash
docker exec postgres_db psql -U <user> -d <db> -c 'select id, user_id, platform, created_at from device;'
```

A row means push is wired end-to-end. Server-side, `APNS_USE_SANDBOX` must be
`true` for an Xcode-installed (development-signed) build and `false` for
TestFlight — a mismatch returns APNs `400 BadDeviceToken`.

## Pointing at a backend

`WishlistKit/WishlistAPI.swift` defaults to the deployed HTTPS host. To aim a
build somewhere else, add a `WLAPIBaseURL` string to the target's `Info.plist`
rather than editing code — both the app and the extension read it:

```xml
<key>WLAPIBaseURL</key>
<string>http://localhost:8000</string>
```

Running against local Flask:

```bash
FLASK_APP=app.py FAMILY_PASSWORD=<code> DATABASE_URL=sqlite:///$(pwd)/instance/demo.sqlite .venv/bin/flask run --port 8000
```

**Use 8000, not 5000** — macOS AirPlay Receiver listens on 5000 and will answer
with `403 AirTunes`, which looks confusingly like an app bug. Both targets carry
an ATS exception for `localhost` only; the production host is HTTPS so it needs
none.

## Simulator quirks worth knowing

These are environment behaviours, not bugs — they cost real debugging time:

- **The token doesn't survive relaunch.** Unsigned builds can't write the shared
  Keychain access group, so `KeychainTokenStore` falls back to an in-memory
  cache. Expect to log in again after each install. Signed builds persist it.
- **The Share Extension always says "open the app and log in".** Same cause: it's
  a separate process and can't read a token that was never written to the shared
  group. Its authenticated save can only be verified on a signed device build.
- **Typing via automation triggers accent popups.** Driving the simulator
  programmatically, prefer pasting (`pbcopy` + `cmd+V`) over synthetic
  keystrokes.

## Testing push notifications

Real APNs needs a signed build on a physical device. The simulator can accept a
payload file, which is enough to exercise deep-link routing:

```bash
xcrun simctl push booted com.reitz.wishlist payload.apns
```

```json
{
  "Simulator Target Bundle": "com.reitz.wishlist",
  "aps": { "alert": { "title": "Wishlist", "body": "Mom claimed an item" } },
  "link": "/items/42"
}
```

Server-side, push also requires `APNS_*` env vars **and** a running Celery
worker with a broker — see [`../docs/DEPLOY_HOME_SERVER.md`](../docs/DEPLOY_HOME_SERVER.md).

## Siri and App Intents

Six intents plus on-screen awareness, backed by `IntentService`
in `WishlistKit` (testable offline) with thin intent structs in
`Wishlist/Intents/`:

| Intent | Kind | Availability |
|---|---|---|
| `AddWishlistItemIntent` | custom | iOS 17+ |
| `AddLinkFromClipboardIntent` | custom | iOS 17+ |
| `ClaimItemIntent` | custom, `requestConfirmation`-gated | iOS 17+ |
| `MyClaimsIntent` | custom | iOS 17+ |
| `SearchWishlistIntent` | `@AppIntent(schema: .system.searchInApp)` | iOS 27+ |
| `OpenWishlistItemIntent` | `@AppIntent(schema: .system.open)` | iOS 27+ |
| On-screen awareness, detail (`ItemDetailView`) | `NSUserActivity.appEntityIdentifier` | iOS 18.2+ |
| On-screen awareness, lists (`ItemRow`) | `.appEntityIdentifier` view modifier | iOS 18.4+ |

Add/claim are custom rather than schema-conformant: the only system schema for
"add to a list" is `.reminders.createReminder`, and adopting it would put this
app in the pool Siri picks from for actual reminders. `.system.search` is
deprecated in favour of `.system.searchInApp`; both it and `.system.open` only
exist from iOS 27 onward. The app's deployment target stays 17.0 — those two
intents are wrapped in `@available(iOS 27, *)` and simply don't exist on older
OSes, same idea for the on-screen-awareness modifiers at 18.2 and 18.4.

On-screen awareness is deliberately **two** annotations, per Apple's guidance:
`.userActivity` on `ItemDetailView` for when a single item fills the screen, and
`.appEntityIdentifier` on `ItemRow` so the system knows which items are in a
list. `ItemRow` is shared by the Family, My List and Claims screens, so one
annotation covers all three. With only the detail half, "claim this" works when
you're looking at one item but not while browsing a list — which is where you'd
more often say it.

Both `.appEntityIdentifier` overloads live in the `_AppIntents_SwiftUI`
cross-import overlay, not in `SwiftUI` or `AppIntents` proper — importing both
in the same file is what brings them in. Grepping only those two frameworks
suggests the modifier doesn't exist; it does.

### AppIntentsTesting doesn't work outside Apple

`AppIntentsTesting` (new in iOS 27, WWDC26 session 295) looks like the answer to
"how do I test Siri integration without a device". It isn't, for us. It ships in
`Xcode-beta.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/Library/Frameworks/`
and links fine from a `bundle.ui-testing` target, but **every functional API
requires an internal Apple build of the OS**:

```
AnyAppIntent.run()                → AppIntentsServicesSecurityErrorDomain 803
                                    "Unable to run internal tests on a Customer build"
AppEntityDefinition.entities(matching:) → same 803
AppEntityDefinition.spotlightQuery(_:)  → "Remote threw needsInternalBuild"
```

Every public simulator runtime and every shipping device is a "Customer build",
so this is a wall, not a configuration problem. A test target was built, run
against the iOS 27 simulator, and removed again.

Two traps worth knowing if you retry this:

- `IntentDefinitions.intents["…"]` and `.entities["…"]` return **non-optional**
  values and do no validation — `intents["NoSuchIntentXYZ"]` yields a perfectly
  good-looking `AppIntentDefinition`. An `XCTAssertNotNil` on one can never
  fail, so "the intent is registered" tests written that way are vacuous.
- Because `.run()` throws the 803 security error, a test shaped like
  "invoking while signed out throws" **passes for entirely the wrong reason**.
  It never reaches the auth gate.

So the honest position stands: intent registration, Siri phrase matching, entity
resolution and the on-screen annotations are verifiable only by hand on a signed
device build.

`AppEnvironment.configureIntents()` (called from `AppDelegate` at launch)
replaces `IntentService.shared`'s default no-token instance with one wired to
the app's real `APIClient`/token store. Before that call — or in any process
that never makes it, see "device-only" below — every intent throws
`.notSignedIn`.

### Trying it (Shortcuts app)

`WishlistShortcuts` (an `AppShortcutsProvider`) registers phrases for the four
**custom** intents only — the two schema-conformant intents have no phrase of
their own and are instead reached through system search / Spotlight / Siri
suggestions, and as actions inside a user-built Shortcut:

- "Add an item to Wishlist" / "Add to my Wishlist" / "Put something on my
  Wishlist"
- "Add my clipboard to Wishlist" / "Add this link to Wishlist"
- "What have I claimed in Wishlist" / "My Wishlist claims"
- "Claim `<item>` in Wishlist"

These show up in the Shortcuts app under Wishlist with no configuration
needed, and can be triggered by voice ("Hey Siri, add to my Wishlist") on a
signed device build that's logged in — on the simulator, every one of them
will instead answer "Open Wishlist and log in first" (see below).

### The two-turn limitation

The obvious headline example — "Add AirPods to my wishlist" as a single
utterance — is **not achievable**. App Intents only allows an `AppShortcut`
phrase to interpolate an `AppEntity` or `AppEnum` parameter; `itemName` on
`AddWishlistItemIntent` is deliberately a free-text `String`, and the metadata
compiler rejects `\(.$itemName)` in a phrase outright. So the shipped phrases
are name-less triggers only ("Add to my Wishlist"), and Siri then asks "What
should I add?" via `requestValueDialog` — a **two-turn** exchange, not
one-shot.

One-shot still works in the three places where no free-text name needs to
ride the phrase:
- `AddLinkFromClipboardIntent` — the link comes off the clipboard, not speech.
- A user-built Shortcut that feeds another action's output into
  `AddWishlistItemIntent`'s `link` parameter.
- `ClaimItemIntent` — its `target` is an `ItemEntity` (an `AppEntity`), so
  `"Claim \(\.$target) in Wishlist"` interpolates fine and resolves in one
  phrase.

### Device-only feature

Every intent calls `IntentService.shared`, which reads the auth token from the
shared Keychain access group via `TokenStoring`. Unsigned simulator builds
can't access that access group (see "Simulator quirks" above), so
`requireToken()` always throws `.notSignedIn` there — every intent correctly
says "Open Wishlist and log in first" on the simulator, regardless of iOS
version. That's expected simulator behaviour, not a bug — the same constraint
that hits push notifications and the Share Extension.

### What can't be verified from a simulator

- Whether Siri actually recognises any of the phrases above, and how Apple
  Intelligence ranks or surfaces the app for search — phrase matching and
  on-device model behaviour aren't reproducible in a simulator build,
  regardless of its OS version.
- The full add/claim/search/open flows end-to-end, since they all need a
  signed-in token — blocked by the device-only Keychain constraint above, not
  by OS availability. (The simulator runtime used for this task's builds
  happens to be iOS 27.0, so `SearchWishlistIntent`, `OpenWishlistItemIntent`,
  and the on-screen-awareness modifier are all compiled in and reachable —
  they just can't complete a real request without a signed build.)

Real verification needs a signed build on a physical iPhone: confirm "Add to
my Wishlist" triggers "What should I add?" and creates the item you speak
back; confirm "Claim `<item>` in Wishlist" resolves in one phrase; and on
iOS 27, confirm search surfaces items in Spotlight and that "claim this"
resolves from the item detail screen.

## Regenerating the app icon

The icon is generated from code so it stays tweakable in review:

```bash
xcrun --sdk macosx swiftc ios/Tools/make_icon.swift -o /tmp/make_icon && /tmp/make_icon ios/Wishlist/Assets.xcassets/AppIcon.appiconset/AppIcon.png
```

## Design system

`Wishlist/Theme.swift` — a "warm editorial" palette (cream / cranberry / gold),
New York serif for display type, card surfaces, monogram avatars, priority dots
and status pills.

Screen titles are rendered as **content** (`WLScreenTitle`), not SwiftUI
navigation titles. Restyling the real navigation bar via
`UINavigationBarAppearance` was tried and reverted: dynamic colors are
snapshotted inside `*TextAttributes` (so a theme color can resolve to the wrong
variant and vanish), and appearance-proxy changes race bar creation. Both
produced an invisible title. Don't re-attempt it without reading that history.

## Surprise protection

The server omits `status` and `last_updated_by` for items you own, so the API
cannot reveal who claimed your gift. The client mirrors that in its types:
`Item.status` is **optional**, `Item.isOwn` is `status == nil`, and `ItemRow`
cannot draw a claim badge without a status. Keep it that way — don't default a
missing status.
