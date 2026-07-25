# Wishlist for iOS

Native SwiftUI client for the family wishlist, talking to the Flask
[`/api/v1`](../docs/API_V1.md) JSON API.

## Layout

| Target | What it is |
|---|---|
| `WishlistKit` | Framework: models, `APIClient`, Keychain token store, view models. Everything testable lives here. |
| `Wishlist` | The app: login + four tabs (Family, My List, Claims, Activity). |
| `ShareExtension` | "Add to Wishlist" from Safari's share sheet. |
| `WishlistKitTests` | Unit tests (45), all offline via a stubbed `URLProtocol`. |

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
