# Siri / App Intents Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add to and query the family wishlist by voice, from Shortcuts, and — on iOS 27 — by referring to what's on screen.

**Architecture:** All logic lives in a testable `IntentService` in `WishlistKit`; the `AppIntent` structs in the app target are thin wrappers (`AppShortcutsProvider` must be in the app target). Read intents conform to Apple's `.system.search` / `.system.open` schemas for Apple Intelligence discoverability; add and claim are custom intents because no schema fits a wishlist.

**Tech Stack:** Swift 6.4, App Intents, SwiftUI, XCTest. Backend: the existing `/api/v1` (unchanged — this plan touches no Python).

Spec: `docs/superpowers/specs/2026-07-25-siri-app-intents-design.md`. Read it first.

## Global Constraints

- **Deployment target stays iOS 17.0.** Tasks 1–5 use iOS 16/17 APIs. Task 6 is `@available(iOS 27, *)`-gated and must not raise the floor.
- Regenerate after adding files: `xcodegen generate --spec ios/project.yml --project-root .` — **the `--project-root .` flag is required.**
- Build/test with the beta toolchain: `export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer`
- Test command: `xcodebuild -project ios/Wishlist.xcodeproj -scheme WishlistKit -destination 'platform=iOS Simulator,name=iPhone 17' test`
- App build: `xcodebuild -project ios/Wishlist.xcodeproj -scheme Wishlist -destination 'platform=iOS Simulator,name=iPhone 17' build`
- **No Python, no API, no existing-screen changes.** Additive only.
- **No user ID is needed anywhere.** There is no `/me` endpoint, and `Item.isOwn` (`status == nil`) already identifies the caller's own items. Do not add identity persistence.
- **Surprise protection:** never default a missing `status`, and never let an intent speak claim status for an item where `isOwn` is true.
- Every `catch` that assigns to a stored property must use `self.` — a bare `catch` binds `error` and shadows it. This has bitten this codebase twice.
- Commit messages end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

## Existing API surface these tasks consume

```swift
// WishlistKit/Networking/APIClient.swift  (actor)
public func users() async throws -> [User]
public func items(userID: Int? = nil, status: String? = nil,
                  category: String? = nil, query: String? = nil) async throws -> [Item]
public func myClaims() async throws -> [Item]
public func createItem(_ draft: ItemDraft) async throws -> Item
public func claim(itemID: Int) async throws -> Item
public func fetchMetadata(url: String) async throws -> ItemDraft

// WishlistKit/Models/Item.swift
public struct Item { id, description, link, price, category, imageURL, priority,
                     size, color, quantity, userID, status: String?, lastUpdatedBy: ItemActor? }
public var isOwn: Bool { status == nil }

// WishlistKit/Networking/APIError.swift
public enum APIError: Error { case unauthorized, conflict(code: String),
                              validation([String]), http(status: Int, code: String?),
                              transport(String), decoding(String) }
```

---

### Task 1: `IntentService` — auth gate and add-item

**Files:**
- Create: `ios/WishlistKit/Intents/IntentService.swift`
- Create: `ios/WishlistKit/Intents/IntentError.swift`
- Test: `ios/WishlistKitTests/IntentServiceTests.swift`

**Interfaces:**
- Consumes: `APIClient`, `TokenStoring`, `ItemDraft`, `APIError`.
- Produces:
  - `public enum IntentError: Error, CustomLocalizedStringResourceConvertible { case notSignedIn, message(String) }`
  - `public struct IntentService: Sendable`
  - `public init(client: APIClient, tokenStore: TokenStoring)`
  - `public func addItem(named: String, url: String?, price: Double?) async throws -> Item`

- [ ] **Step 1: Write the failing test**

Create `ios/WishlistKitTests/IntentServiceTests.swift`:

```swift
import XCTest
@testable import WishlistKit

final class IntentServiceTests: XCTestCase {
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    private func service(token: String? = "tok",
                         _ respond: @escaping (URLRequest) -> (Int, String) = { _ in (200, "{}") })
        -> IntentService {
        StubURLProtocol.handler = { req in
            let (status, json) = respond(req)
            return (HTTPURLResponse(url: req.url!, statusCode: status, httpVersion: nil, headerFields: nil)!,
                    Data(json.utf8))
        }
        let store = InMemoryTokenStore()
        if let token { store.save(token) }
        let client = APIClient(baseURL: URL(string: "http://t.local")!,
                               session: StubURLProtocol.session(),
                               tokenProvider: { store.read() })
        return IntentService(client: client, tokenStore: store)
    }

    func testAddItemPostsAndReturnsItem() async throws {
        var body: [String: Any]?
        let svc = service { req in
            body = Self.jsonBody(req)
            return (201, #"{"item":{"id":9,"description":"AirPods Pro","user_id":1}}"#)
        }

        let item = try await svc.addItem(named: "AirPods Pro", url: nil, price: nil)

        XCTAssertEqual(item.description, "AirPods Pro")
        XCTAssertEqual(body?["description"] as? String, "AirPods Pro")
    }

    func testAddItemWithoutTokenFailsBeforeAnyNetworkCall() async {
        var called = false
        let svc = service(token: nil) { _ in called = true; return (201, "{}") }

        do {
            _ = try await svc.addItem(named: "AirPods", url: nil, price: nil)
            XCTFail("expected notSignedIn")
        } catch IntentError.notSignedIn {
            XCTAssertFalse(called, "must not hit the network when signed out")
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    func testUnauthorizedMidFlightBecomesNotSignedIn() async {
        let svc = service { _ in (401, #"{"error":"unauthorized"}"#) }

        do {
            _ = try await svc.addItem(named: "AirPods", url: nil, price: nil)
            XCTFail("expected notSignedIn")
        } catch IntentError.notSignedIn {
            // correct: a revoked token reads the same as being signed out
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    func testValidationErrorSurfacesServerMessage() async {
        let svc = service { _ in (400, #"{"errors":["Description is required."]}"#) }

        do {
            _ = try await svc.addItem(named: " ", url: nil, price: nil)
            XCTFail("expected message")
        } catch IntentError.message(let text) {
            XCTAssertEqual(text, "Description is required.")
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    static func jsonBody(_ req: URLRequest) -> [String: Any]? {
        if let data = req.httpBody {
            return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        }
        guard let stream = req.httpBodyStream else { return nil }
        stream.open(); defer { stream.close() }
        var data = Data(); var buf = [UInt8](repeating: 0, count: 4096)
        while stream.hasBytesAvailable {
            let read = stream.read(&buf, maxLength: buf.count)
            if read <= 0 { break }
            data.append(buf, count: read)
        }
        return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    }
}
```

- [ ] **Step 2: Run to verify it fails**

```bash
export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
xcodegen generate --spec ios/project.yml --project-root .
xcodebuild -project ios/Wishlist.xcodeproj -scheme WishlistKit -destination 'platform=iOS Simulator,name=iPhone 17' test 2>&1 | grep -E "error:|TEST (SUCCEEDED|FAILED)"
```
Expected: compile failure — `cannot find 'IntentService' in scope`.

- [ ] **Step 3: Implement the error type**

Create `ios/WishlistKit/Intents/IntentError.swift`:

```swift
import AppIntents
import Foundation

/// Errors an intent can surface to Siri. Conforming to
/// `CustomLocalizedStringResourceConvertible` is what lets Siri *speak* the
/// reason instead of a generic failure.
public enum IntentError: Error, CustomLocalizedStringResourceConvertible {
    /// No token, or the token was rejected. Same message either way — from the
    /// user's point of view "signed out" and "token expired" are the same fix.
    case notSignedIn
    /// A reason from the server or a business rule, already phrased for speech.
    case message(String)

    public var localizedStringResource: LocalizedStringResource {
        switch self {
        case .notSignedIn:
            return "Open Wishlist and log in first."
        case .message(let text):
            return LocalizedStringResource(stringLiteral: text)
        }
    }
}
```

- [ ] **Step 4: Implement the service**

Create `ios/WishlistKit/Intents/IntentService.swift`:

```swift
import Foundation

/// Business logic behind the App Intents. Lives here rather than in the intent
/// structs so it can be tested offline against a stubbed URLProtocol — the
/// intents themselves are thin wrappers.
public struct IntentService: Sendable {
    private let client: APIClient
    private let tokenStore: TokenStoring

    public init(client: APIClient, tokenStore: TokenStoring) {
        self.client = client
        self.tokenStore = tokenStore
    }

    /// App Intents and `EntityQuery` are instantiated by the system with no
    /// arguments, so they cannot be given a service by injection. The app
    /// replaces this at launch via `AppEnvironment.configureIntents()`; until
    /// then it has no token and every call fails as `notSignedIn`, which is the
    /// correct behaviour rather than a crash.
    nonisolated(unsafe) public static var shared = IntentService(
        client: APIClient(baseURL: WishlistAPI.defaultBaseURL, tokenProvider: { nil }),
        tokenStore: InMemoryTokenStore()
    )

    /// Deliberately not `private`: later extensions in this file call it.
    func requireToken() throws {
        guard let token = tokenStore.read(), !token.isEmpty else {
            throw IntentError.notSignedIn
        }
    }

    public func addItem(named name: String, url: String?, price: Double?) async throws -> Item {
        try requireToken()
        let draft = ItemDraft(description: name, link: url, price: price)
        do {
            return try await client.createItem(draft)
        } catch {
            throw Self.translate(error)
        }
    }

    /// Maps API errors onto something Siri can say out loud.
    static func translate(_ error: Error) -> IntentError {
        switch error {
        case APIError.unauthorized:
            return .notSignedIn
        case APIError.validation(let messages):
            return .message(messages.first ?? "Please check the details and try again.")
        case APIError.conflict(let code):
            return .message(friendly(code))
        case is APIError:
            return .message("Couldn't reach the wishlist. Try again.")
        default:
            return .message("Something went wrong. Try again.")
        }
    }

    /// Same copy the app already shows for these conflicts, so voice and screen agree.
    static func friendly(_ code: String) -> String {
        switch code {
        case "own_item": "You can't claim your own item."
        case "not_available": "Someone already claimed this."
        case "already_purchased": "This item is already purchased."
        case "claimed_by_other": "This item is claimed by someone else."
        default: "That action isn't allowed."
        }
    }
}
```

- [ ] **Step 5: Run to verify it passes**

```bash
xcodegen generate --spec ios/project.yml --project-root .
xcodebuild -project ios/Wishlist.xcodeproj -scheme WishlistKit -destination 'platform=iOS Simulator,name=iPhone 17' test 2>&1 | grep -E "Executed [0-9]+ tests, with|TEST (SUCCEEDED|FAILED)"
```
Expected: `TEST SUCCEEDED`, 4 new tests passing (49 total).

- [ ] **Step 6: Commit**

```bash
git add ios/WishlistKit/Intents ios/WishlistKitTests/IntentServiceTests.swift
git commit -m "feat(ios): IntentService with auth gate and add-item

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Add intents — spoken name, link prefill, clipboard

**Files:**
- Create: `ios/Wishlist/Intents/AddWishlistItemIntent.swift`
- Create: `ios/Wishlist/Intents/AddLinkFromClipboardIntent.swift`
- Create: `ios/Wishlist/Intents/WishlistShortcuts.swift`
- Modify: `ios/WishlistKit/Intents/IntentService.swift` (add `addFromLink`)
- Modify: `ios/Wishlist/AppEnvironment.swift` (add an `intentService` accessor)
- Modify: `ios/Wishlist/AppDelegate.swift` (call `configureIntents()`)
- Test: `ios/WishlistKitTests/IntentServiceTests.swift` (append)

**Interfaces:**
- Consumes: `IntentService.addItem(named:url:price:)`, `IntentService.shared`, `APIClient.fetchMetadata(url:)`, `ItemDraft`, `AppEnvironment.client`, `AppEnvironment.tokenStore`.
- Produces: `AddWishlistItemIntent` with `@Parameter var itemName: String`, `@Parameter var link: String?`; `AddLinkFromClipboardIntent`; `IntentService.addFromLink(_:) async throws -> Item`; `WishlistShortcuts: AppShortcutsProvider`; `AppEnvironment.intentService` and `AppEnvironment.configureIntents()`.

- [ ] **Step 1: Point the shared service at the real dependencies**

In `ios/Wishlist/AppEnvironment.swift`, add inside `enum AppEnvironment`:

```swift
    /// Non-isolated so App Intents can reach it outside the main actor.
    static let intentService = IntentService(client: client, tokenStore: tokenStore)

    /// Must run before any intent executes or entity resolves.
    static func configureIntents() {
        IntentService.shared = intentService
    }
```

In `ios/Wishlist/AppDelegate.swift`, make this the first line of
`didFinishLaunchingWithOptions`:

```swift
        AppEnvironment.configureIntents()
```

- [ ] **Step 2: Write the intent**

Create `ios/Wishlist/Intents/AddWishlistItemIntent.swift`:

```swift
import AppIntents
import WishlistKit

/// "Add AirPods Pro to my wishlist."
///
/// Custom rather than schema-conformant: the only schema offering "create an
/// item in a list" is `.reminders.createReminder`, and adopting it would enter
/// this app into the pool Siri picks from for real reminders. See the design
/// spec for the full reasoning.
struct AddWishlistItemIntent: AppIntent {
    static var title: LocalizedStringResource = "Add to Wishlist"
    static var description = IntentDescription(
        "Adds an item to your family wishlist.",
        categoryName: "Wishlist"
    )

    /// Requesting a value means Siri prompts for it rather than failing when
    /// the phrase carries no item name.
    @Parameter(title: "Item", requestValueDialog: "What should I add?")
    var itemName: String

    /// Optional so the same intent serves Shortcuts and the Action button,
    /// where a URL is passed instead of spoken.
    @Parameter(title: "Link")
    var link: String?

    static var parameterSummary: some ParameterSummary {
        Summary("Add \(\.$itemName) to my wishlist")
    }

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let item = try await IntentService.shared.addItem(
            named: itemName, url: link, price: nil
        )
        return .result(dialog: "Added \(item.description) to your wishlist.")
    }
}
```

- [ ] **Step 3: Write the failing test for link prefill**

Append to `ios/WishlistKitTests/IntentServiceTests.swift`:

```swift
    func testAddFromLinkPrefillsDescriptionFromMetadata() async throws {
        var paths: [String] = []
        let svc = service { req in
            paths.append(req.url?.path ?? "")
            if req.url?.path.contains("metadata") == true {
                return (200, #"{"description":"Cashmere Blanket","price":89.0,"link":"https://shop.test/b"}"#)
            }
            return (201, #"{"item":{"id":4,"description":"Cashmere Blanket","user_id":1}}"#)
        }

        let item = try await svc.addFromLink("https://shop.test/b")

        XCTAssertEqual(item.description, "Cashmere Blanket")
        XCTAssertTrue(paths.contains { $0.contains("metadata") }, "should fetch metadata first")
    }

    func testAddFromLinkFallsBackToURLWhenMetadataFails() async throws {
        let svc = service { req in
            if req.url?.path.contains("metadata") == true {
                return (502, #"{"error":"fetch_failed"}"#)
            }
            return (201, #"{"item":{"id":5,"description":"https://shop.test/b","user_id":1}}"#)
        }

        // A dead scraper must not block saving the link — it is still useful.
        let item = try await svc.addFromLink("https://shop.test/b")

        XCTAssertEqual(item.description, "https://shop.test/b")
    }

    func testAddFromLinkRejectsNonURLText() async {
        let svc = service { _ in (201, "{}") }

        do {
            _ = try await svc.addFromLink("just some words")
            XCTFail("expected message")
        } catch IntentError.message(let text) {
            XCTAssertEqual(text, "That doesn't look like a link.")
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }
```

- [ ] **Step 4: Run to verify it fails**

Run:
```bash
xcodebuild -project ios/Wishlist.xcodeproj -scheme WishlistKit -destination 'platform=iOS Simulator,name=iPhone 17' test 2>&1 | grep -E "error:|Testing failed"
```
Expected: compile error — `value of type 'IntentService' has no member 'addFromLink'`.

- [ ] **Step 5: Implement link prefill**

Append to `ios/WishlistKit/Intents/IntentService.swift`, inside `IntentService`:

```swift
    /// Saves a URL, prefilling name and price from `/api/v1/metadata`.
    ///
    /// Metadata failure is deliberately non-fatal: the scrapers are best-effort
    /// and a saved bare link still beats a spoken error.
    public func addFromLink(_ raw: String) async throws -> Item {
        try requireToken()

        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed),
              let scheme = url.scheme?.lowercased(),
              scheme == "http" || scheme == "https",
              url.host != nil else {
            throw IntentError.message("That doesn't look like a link.")
        }

        // ItemDraft.description is `String?`; the URL is the fallback name.
        var draft = ItemDraft(description: trimmed, link: trimmed)
        if let fetched = try? await client.fetchMetadata(url: trimmed) {
            if let name = fetched.description, !name.isEmpty { draft.description = name }
            draft.price = fetched.price
            draft.imageURL = fetched.imageURL
        }

        do {
            return try await client.createItem(draft)
        } catch {
            throw Self.translate(error)
        }
    }
```

- [ ] **Step 6: Add the clipboard intent**

Create `ios/Wishlist/Intents/AddLinkFromClipboardIntent.swift`:

```swift
import AppIntents
import UIKit
import WishlistKit

/// "Add my clipboard to my wishlist."
///
/// Reading `UIPasteboard` shows the system's paste confirmation the first time,
/// which is correct — an intent should not silently read the clipboard. Users who
/// want zero friction can instead build a Shortcut that feeds Get Clipboard into
/// `AddWishlistItemIntent`'s `link` parameter.
struct AddLinkFromClipboardIntent: AppIntent {
    static var title: LocalizedStringResource = "Add Link from Clipboard"
    static var description = IntentDescription(
        "Adds the link on your clipboard to your family wishlist.",
        categoryName: "Wishlist"
    )

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        guard let text = UIPasteboard.general.string,
              !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return .result(dialog: "There's nothing on your clipboard.")
        }
        let item = try await IntentService.shared.addFromLink(text)
        return .result(dialog: "Added \(item.description) to your wishlist.")
    }
}
```

Then extend `AddWishlistItemIntent.perform()` so a link with no spoken name also
prefills. Replace its body with:

```swift
    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let trimmedName = itemName.trimmingCharacters(in: .whitespacesAndNewlines)
        let item: Item
        if trimmedName.isEmpty, let link, !link.isEmpty {
            item = try await IntentService.shared.addFromLink(link)
        } else {
            item = try await IntentService.shared.addItem(
                named: trimmedName, url: link, price: nil
            )
        }
        return .result(dialog: "Added \(item.description) to your wishlist.")
    }
```

- [ ] **Step 7: Write the shortcuts provider**

Create `ios/Wishlist/Intents/WishlistShortcuts.swift`:

```swift
import AppIntents

/// Phrases Siri recognises without the user configuring anything. Every phrase
/// must contain `\(.applicationName)` — App Intents requires it, and it is what
/// disambiguates this app from other list apps.
struct WishlistShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: AddWishlistItemIntent(),
            phrases: [
                "Add \(\.$itemName) to \(.applicationName)",
                "Add \(\.$itemName) to my \(.applicationName)",
                "Put \(\.$itemName) on my \(.applicationName)",
            ],
            shortTitle: "Add to Wishlist",
            systemImageName: "gift"
        )
        AppShortcut(
            intent: AddLinkFromClipboardIntent(),
            phrases: [
                "Add my clipboard to \(.applicationName)",
                "Add this link to \(.applicationName)",
            ],
            shortTitle: "Add Clipboard Link",
            systemImageName: "link"
        )
    }
}
```

- [ ] **Step 8: Run the tests and build the app target**

```bash
xcodegen generate --spec ios/project.yml --project-root .
xcodebuild -project ios/Wishlist.xcodeproj -scheme WishlistKit -destination 'platform=iOS Simulator,name=iPhone 17' test 2>&1 | grep -E "Test Suite .* (passed|failed)|error:"
xcodebuild -project ios/Wishlist.xcodeproj -scheme Wishlist -destination 'platform=iOS Simulator,name=iPhone 17' build 2>&1 | grep -E "BUILD (SUCCEEDED|FAILED)|error:"
```
Expected: all tests pass, then `BUILD SUCCEEDED`. If the compiler rejects a phrase, it is almost always the missing `\(.applicationName)` token.

- [ ] **Step 9: Verify the intents are registered**

```bash
xcrun simctl install <BOOTED_UDID> "$(xcodebuild -project ios/Wishlist.xcodeproj -scheme Wishlist -destination 'platform=iOS Simulator,name=iPhone 17' -showBuildSettings 2>/dev/null | awk '/BUILT_PRODUCTS_DIR/{print $3}')/Wishlist.app"
```

Then open the **Shortcuts** app in the simulator and confirm both "Add to Wishlist" and "Add Clipboard Link" appear under the Wishlist app. Signed-out behaviour is expected here — the simulator can't read the shared Keychain, so running it should say "Open Wishlist and log in first." **That is a pass, not a failure**: it proves the auth gate speaks rather than crashing.

- [ ] **Step 10: Commit**

```bash
git add ios/Wishlist/Intents ios/Wishlist/AppEnvironment.swift ios/Wishlist/AppDelegate.swift \
        ios/WishlistKit/Intents/IntentService.swift ios/WishlistKitTests/IntentServiceTests.swift
git commit -m "feat(ios): add-item intents with link prefill and Siri phrases

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `ItemEntity` and the query, with surprise protection

**Files:**
- Create: `ios/WishlistKit/Intents/ItemEntity.swift`
- Modify: `ios/WishlistKit/Intents/IntentService.swift` (add `searchItems`, `itemsForOwner`)
- Test: `ios/WishlistKitTests/ItemEntityTests.swift`

**Interfaces:**
- Consumes: `Item`, `IntentService`.
- Produces:
  - `public struct ItemEntity: AppEntity, Sendable` with `id: Int`, `name: String`, `ownerName: String?`, `price: Double?`, `status: String?`
  - `public init(item: Item, ownerName: String?)`
  - `public struct WishlistItemQuery: EntityStringQuery`
  - `IntentService.searchItems(matching: String) async throws -> [ItemEntity]`
  - `IntentService.entities(for ids: [Int]) async throws -> [ItemEntity]`

- [ ] **Step 1: Write the failing test**

Create `ios/WishlistKitTests/ItemEntityTests.swift`:

```swift
import XCTest
@testable import WishlistKit

final class ItemEntityTests: XCTestCase {
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    private func decodeItem(_ json: String) throws -> Item {
        try JSONDecoder().decode(Item.self, from: Data(json.utf8))
    }

    func testOwnItemCarriesNoStatus() throws {
        // Server omits status for the caller's own items.
        let item = try decodeItem(#"{"id":1,"description":"Bike","user_id":7}"#)
        let entity = ItemEntity(item: item, ownerName: nil)

        XCTAssertNil(entity.status)
        XCTAssertTrue(item.isOwn)
    }

    func testOthersItemKeepsStatus() throws {
        let item = try decodeItem(#"{"id":2,"description":"Book","user_id":9,"status":"Claimed"}"#)
        let entity = ItemEntity(item: item, ownerName: "Mom")

        XCTAssertEqual(entity.status, "Claimed")
        XCTAssertEqual(entity.ownerName, "Mom")
    }

    func testSpokenDescriptionNeverLeaksOwnItemStatus() throws {
        // The display representation is what Siri reads aloud. For an own item it
        // must not imply anything about claims — that is the whole invariant.
        let own = ItemEntity(item: try decodeItem(#"{"id":1,"description":"Bike","user_id":7}"#),
                             ownerName: nil)
        let spoken = "\(own.displayRepresentation.title)"

        XCTAssertTrue(spoken.contains("Bike"))
        for banned in ["Claimed", "Purchased", "Available"] {
            XCTAssertFalse(spoken.contains(banned), "own item leaked \(banned)")
        }
    }

    func testSearchReturnsMatchingEntities() async throws {
        StubURLProtocol.handler = { req in
            let json = req.url!.path.hasSuffix("/users")
                ? #"{"users":[{"id":9,"name":"Mom","email":"m@x.com"}]}"#
                : #"{"items":[{"id":2,"description":"Cashmere throw","user_id":9,"status":"Available"}]}"#
            return (HTTPURLResponse(url: req.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!,
                    Data(json.utf8))
        }
        let store = InMemoryTokenStore(); store.save("tok")
        let client = APIClient(baseURL: URL(string: "http://t.local")!,
                               session: StubURLProtocol.session(),
                               tokenProvider: { store.read() })
        let svc = IntentService(client: client, tokenStore: store)

        let results = try await svc.searchItems(matching: "cashmere")

        XCTAssertEqual(results.count, 1)
        XCTAssertEqual(results.first?.name, "Cashmere throw")
        XCTAssertEqual(results.first?.ownerName, "Mom")
    }
}
```

- [ ] **Step 2: Run to verify it fails**

Run the WishlistKit test command. Expected: `cannot find 'ItemEntity' in scope`.

- [ ] **Step 3: Implement the entity**

Create `ios/WishlistKit/Intents/ItemEntity.swift`:

```swift
import AppIntents
import Foundation

/// An item as Siri sees it.
///
/// `status` is optional and absent for the caller's own items, mirroring the
/// server's serializer. `displayRepresentation` — the text Siri speaks — must
/// never mention claim state for an own item.
public struct ItemEntity: AppEntity, Sendable {
    public let id: Int
    public let name: String
    public let ownerName: String?
    public let price: Double?
    public let status: String?

    public init(item: Item, ownerName: String?) {
        self.id = item.id
        self.name = item.description
        self.ownerName = ownerName
        self.price = item.price
        self.status = item.status      // nil for own items — never defaulted
    }

    public static var typeDisplayRepresentation: TypeDisplayRepresentation = "Wishlist Item"

    public var displayRepresentation: DisplayRepresentation {
        var subtitleParts: [String] = []
        if let ownerName { subtitleParts.append(ownerName) }
        if let price {
            subtitleParts.append(price.formatted(.currency(code: "USD")))
        }
        // Claim state is spoken only for other people's items. For an own item
        // `status` is nil, so nothing to leak.
        if let status, status != "Available" { subtitleParts.append(status) }

        return DisplayRepresentation(
            title: "\(name)",
            subtitle: subtitleParts.isEmpty ? nil : "\(subtitleParts.joined(separator: " · "))"
        )
    }

    public static var defaultQuery = WishlistItemQuery()
}

/// Resolves entities by id (for "open this") and by spoken text (for search).
public struct WishlistItemQuery: EntityStringQuery {
    public init() {}

    public func entities(for identifiers: [ItemEntity.ID]) async throws -> [ItemEntity] {
        try await IntentService.shared.entities(for: identifiers)
    }

    public func entities(matching string: String) async throws -> [ItemEntity] {
        try await IntentService.shared.searchItems(matching: string)
    }
}
```

- [ ] **Step 4: Add the shared instance and query methods**

`WishlistItemQuery` is constructed by the system with no arguments, so it needs a
service it can reach. Add to `ios/WishlistKit/Intents/IntentService.swift`:

```swift
extension IntentService {
    /// Owner names for entity subtitles, resolved once per query.
    /// Not `private` — Task 5's extension calls it too.
    func ownerNames() async throws -> [Int: String] {
        Dictionary(uniqueKeysWithValues: try await client.users().map { ($0.id, $0.name) })
    }

    public func searchItems(matching text: String) async throws -> [ItemEntity] {
        try requireToken()
        do {
            let names = try await ownerNames()
            let items = try await client.items(query: text)
            return items.map { ItemEntity(item: $0, ownerName: names[$0.userID]) }
        } catch {
            throw Self.translate(error)
        }
    }

    public func entities(for ids: [Int]) async throws -> [ItemEntity] {
        try requireToken()
        do {
            let names = try await ownerNames()
            let wanted = Set(ids)
            return try await client.items()
                .filter { wanted.contains($0.id) }
                .map { ItemEntity(item: $0, ownerName: names[$0.userID]) }
        } catch {
            throw Self.translate(error)
        }
    }
}
```

`IntentService.shared` and `AppEnvironment.configureIntents()` already exist from
Tasks 1 and 2 — nothing further to wire here.

- [ ] **Step 5: Run to verify it passes**

Run the WishlistKit test command. Expected: `TEST SUCCEEDED`, 4 new tests (53 total).

- [ ] **Step 6: Commit**

```bash
git add ios/WishlistKit/Intents ios/WishlistKitTests/ItemEntityTests.swift 
git commit -m "feat(ios): ItemEntity and query, with own-item status never spoken

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Schema-conformant search and open

**Files:**
- Create: `ios/Wishlist/Intents/SearchWishlistIntent.swift`
- Create: `ios/Wishlist/Intents/OpenWishlistItemIntent.swift`
- Modify: `ios/Wishlist/Views/RootTabView.swift` (handle an open request)

**Interfaces:**
- Consumes: `ItemEntity`, `IntentService.searchItems(matching:)`.
- Produces: `SearchWishlistIntent` conforming to `.system.search`; `OpenWishlistItemIntent` conforming to `.system.open`; `Notification.Name.wishlistOpenItem`.

- [ ] **Step 1: Discover the schemas' required shape (do this first)**

The `@AppIntent(schema:)` macro is **compiler-checked**: it fails the build with
the exact members a schema requires. Use that rather than guessing. Create
`ios/Wishlist/Intents/SearchWishlistIntent.swift` with a deliberately incomplete
conformance:

```swift
import AppIntents
import WishlistKit

@AppIntent(schema: .system.search)
struct SearchWishlistIntent: AppIntent {
    static var title: LocalizedStringResource = "Search Wishlist"

    func perform() async throws -> some IntentResult {
        .result()
    }
}
```

```bash
xcodegen generate --spec ios/project.yml --project-root .
xcodebuild -project ios/Wishlist.xcodeproj -scheme Wishlist -destination 'platform=iOS Simulator,name=iPhone 17' build 2>&1 | grep -E "error:" | head -20
```

**Record the compiler's required members verbatim in the commit message.** They
are the authoritative signature; the code in the next step is the expected shape
but must be reconciled with whatever the macro demands.

- [ ] **Step 2: Implement search against the schema**

Adjust to satisfy the macro. The expected shape:

```swift
import AppIntents
import WishlistKit

/// Conforms to `.system.search`, which is explicitly not category-specific —
/// any app that can search its content may adopt it. This is what gives the
/// read side Apple Intelligence discoverability.
@AppIntent(schema: .system.search)
struct SearchWishlistIntent: AppIntent {
    static var title: LocalizedStringResource = "Search Wishlist"

    @Parameter(title: "Search")
    var criteria: StringSearchCriteria

    func perform() async throws -> some IntentResult & ReturnsValue<[ItemEntity]> {
        let results = try await IntentService.shared.searchItems(matching: criteria.term)
        return .result(value: results)
    }
}
```

If the macro requires a different parameter name or type, use its version and
keep the body — the only project-specific part is the `searchItems` call.

- [ ] **Step 3: Implement open**

Create `ios/Wishlist/Intents/OpenWishlistItemIntent.swift`:

```swift
import AppIntents
import Foundation
import WishlistKit

/// Conforms to `.system.open` so "open the blanket in Wishlist" works and pairs
/// with search results.
@AppIntent(schema: .system.open)
struct OpenWishlistItemIntent: AppIntent {
    static var title: LocalizedStringResource = "Open Wishlist Item"
    static var openAppWhenRun: Bool = true

    @Parameter(title: "Item")
    var target: ItemEntity

    @MainActor
    func perform() async throws -> some IntentResult {
        NotificationCenter.default.post(
            name: .wishlistOpenItem, object: nil, userInfo: ["itemID": target.id]
        )
        return .result()
    }
}

public extension Notification.Name {
    static let wishlistOpenItem = Notification.Name("WishlistOpenItem")
}
```

- [ ] **Step 4: Route the open request to the Family tab**

In `ios/Wishlist/Views/RootTabView.swift`, add alongside the existing
`onReceive` for push deep links:

```swift
        .onReceive(NotificationCenter.default.publisher(for: .wishlistOpenItem)) { _ in
            selectedTab = 0
        }
```

- [ ] **Step 5: Build and verify both compile against their schemas**

```bash
xcodebuild -project ios/Wishlist.xcodeproj -scheme Wishlist -destination 'platform=iOS Simulator,name=iPhone 17' build 2>&1 | grep -E "BUILD (SUCCEEDED|FAILED)|error:"
```
Expected: `BUILD SUCCEEDED`. A successful build *is* the schema-conformance test —
the macro would reject a mismatched shape.

- [ ] **Step 6: Commit**

Substitute the real text for `REPLACE_WITH_STEP_1_OUTPUT` — do not commit the
token literally. It exists because only the run can know what the macro said.

```bash
git add ios/Wishlist/Intents ios/Wishlist/Views/RootTabView.swift
git commit -m "feat(ios): schema-conformant search and open intents

Conforms to .system.search and .system.open. Required member list reported by
the macro: REPLACE_WITH_STEP_1_OUTPUT.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Claim and my-claims intents

**Files:**
- Create: `ios/Wishlist/Intents/ClaimItemIntent.swift`
- Create: `ios/Wishlist/Intents/MyClaimsIntent.swift`
- Modify: `ios/WishlistKit/Intents/IntentService.swift` (add `claim`, `myClaims`)
- Modify: `ios/Wishlist/Intents/WishlistShortcuts.swift` (add phrases)
- Test: `ios/WishlistKitTests/IntentServiceClaimTests.swift`

**Interfaces:**
- Consumes: `ItemEntity`, `APIClient.claim(itemID:)`, `APIClient.myClaims()`.
- Produces: `IntentService.claim(itemID: Int) async throws -> Item`, `IntentService.myClaims() async throws -> [ItemEntity]`.

- [ ] **Step 1: Write the failing test**

Create `ios/WishlistKitTests/IntentServiceClaimTests.swift`:

```swift
import XCTest
@testable import WishlistKit

final class IntentServiceClaimTests: XCTestCase {
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    private func service(_ respond: @escaping (URLRequest) -> (Int, String)) -> IntentService {
        StubURLProtocol.handler = { req in
            let (status, json) = respond(req)
            return (HTTPURLResponse(url: req.url!, statusCode: status, httpVersion: nil, headerFields: nil)!,
                    Data(json.utf8))
        }
        let store = InMemoryTokenStore(); store.save("tok")
        let client = APIClient(baseURL: URL(string: "http://t.local")!,
                               session: StubURLProtocol.session(),
                               tokenProvider: { store.read() })
        return IntentService(client: client, tokenStore: store)
    }

    func testClaimSucceeds() async throws {
        let svc = service { _ in
            (200, #"{"item":{"id":5,"description":"Book","user_id":9,"status":"Claimed"}}"#)
        }
        let item = try await svc.claim(itemID: 5)
        XCTAssertEqual(item.status, "Claimed")
    }

    func testClaimingOwnItemSpeaksTheReason() async {
        let svc = service { _ in (409, #"{"error":"own_item"}"#) }
        do {
            _ = try await svc.claim(itemID: 1)
            XCTFail("expected message")
        } catch IntentError.message(let text) {
            XCTAssertEqual(text, "You can't claim your own item.")
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    func testAlreadyClaimedSpeaksTheReason() async {
        let svc = service { _ in (409, #"{"error":"not_available"}"#) }
        do {
            _ = try await svc.claim(itemID: 1)
            XCTFail("expected message")
        } catch IntentError.message(let text) {
            XCTAssertEqual(text, "Someone already claimed this.")
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    func testMyClaimsReturnsEntities() async throws {
        let svc = service { req in
            req.url!.path.hasSuffix("/users")
                ? (200, #"{"users":[{"id":9,"name":"Mom","email":"m@x.com"}]}"#)
                : (200, #"{"items":[{"id":5,"description":"Book","user_id":9,"status":"Claimed"}]}"#)
        }
        let claims = try await svc.myClaims()
        XCTAssertEqual(claims.map(\.name), ["Book"])
        XCTAssertEqual(claims.first?.ownerName, "Mom")
    }
}
```

- [ ] **Step 2: Run to verify it fails**

Run the WishlistKit test command. Expected: `value of type 'IntentService' has no member 'claim'`.

- [ ] **Step 3: Implement the service methods**

Append to the `extension IntentService` in `ios/WishlistKit/Intents/IntentService.swift`:

```swift
    public func claim(itemID: Int) async throws -> Item {
        try requireToken()
        do {
            return try await client.claim(itemID: itemID)
        } catch {
            throw Self.translate(error)
        }
    }

    public func myClaims() async throws -> [ItemEntity] {
        try requireToken()
        do {
            let names = try await ownerNames()
            return try await client.myClaims().map { ItemEntity(item: $0, ownerName: names[$0.userID]) }
        } catch {
            throw Self.translate(error)
        }
    }
```

- [ ] **Step 4: Write the intents**

Create `ios/Wishlist/Intents/ClaimItemIntent.swift`:

```swift
import AppIntents
import WishlistKit

/// "Claim the blanket." On iOS 27, also "claim this" via on-screen awareness.
///
/// Confirmation is required: claiming changes what other people see, and a
/// misheard item name would otherwise commit silently.
struct ClaimItemIntent: AppIntent {
    static var title: LocalizedStringResource = "Claim Item"
    static var description = IntentDescription(
        "Claims a family member's wishlist item so others know it's taken.",
        categoryName: "Wishlist"
    )

    @Parameter(title: "Item")
    var target: ItemEntity

    static var parameterSummary: some ParameterSummary {
        Summary("Claim \(\.$target)")
    }

    func perform() async throws -> some IntentResult & ProvidesDialog {
        try await requestConfirmation(
            result: .result(dialog: "Claim \(target.name)?")
        )
        let item = try await IntentService.shared.claim(itemID: target.id)
        return .result(dialog: "Claimed \(item.description).")
    }
}
```

Create `ios/Wishlist/Intents/MyClaimsIntent.swift`:

```swift
import AppIntents
import WishlistKit

/// "What have I claimed?" Read-only, and safe to speak: these are by definition
/// other people's items, never the caller's own.
struct MyClaimsIntent: AppIntent {
    static var title: LocalizedStringResource = "My Claims"
    static var description = IntentDescription(
        "Lists the items you've claimed for other people.",
        categoryName: "Wishlist"
    )

    func perform() async throws -> some IntentResult & ReturnsValue<[ItemEntity]> & ProvidesDialog {
        let claims = try await IntentService.shared.myClaims()
        let dialog: IntentDialog = claims.isEmpty
            ? "You haven't claimed anything yet."
            : "You've claimed \(claims.count) \(claims.count == 1 ? "item" : "items")."
        return .result(value: claims, dialog: dialog)
    }
}
```

- [ ] **Step 5: Add the phrases**

In `ios/Wishlist/Intents/WishlistShortcuts.swift`, add to `appShortcuts` after the
existing `AppShortcut`:

```swift
        AppShortcut(
            intent: MyClaimsIntent(),
            phrases: [
                "What have I claimed in \(.applicationName)",
                "My \(.applicationName) claims",
            ],
            shortTitle: "My Claims",
            systemImageName: "checkmark.circle"
        )
```

`ClaimItemIntent` is deliberately **not** given a top-level phrase: it needs an
item to act on, and a bare "claim" phrase with no resolvable target is a bad
voice experience. It surfaces through Shortcuts, entity resolution, and (Task 6)
on-screen awareness.

- [ ] **Step 6: Run tests and build**

```bash
xcodebuild -project ios/Wishlist.xcodeproj -scheme WishlistKit -destination 'platform=iOS Simulator,name=iPhone 17' test 2>&1 | grep -E "Executed [0-9]+ tests, with|TEST (SUCCEEDED|FAILED)"
xcodebuild -project ios/Wishlist.xcodeproj -scheme Wishlist -destination 'platform=iOS Simulator,name=iPhone 17' build 2>&1 | grep -E "BUILD (SUCCEEDED|FAILED)|error:"
```
Expected: `TEST SUCCEEDED` (4 new, 57 total) and `BUILD SUCCEEDED`.

- [ ] **Step 7: Commit**

```bash
git add ios/WishlistKit/Intents ios/WishlistKitTests/IntentServiceClaimTests.swift ios/Wishlist/Intents
git commit -m "feat(ios): claim and my-claims intents, with confirmation before claiming

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: iOS 27 on-screen awareness

**Files:**
- Modify: `ios/Wishlist/Views/ItemRow.swift`
- Modify: `ios/Wishlist/Views/ItemDetailView.swift`
- Modify: `ios/Wishlist/Views/MemberItemsView.swift`

**Interfaces:**
- Consumes: `ItemEntity` (Task 3), `ClaimItemIntent` (Task 5).
- Produces: no new symbols — annotations only.

⚠️ **The APIs in this task are unverified.** They postdate the plan author's
knowledge and Apple's documentation pages did not render for automated reading.
Step 1 is verification, not implementation. Do not skip it, and do not let this
task block Tasks 1–5, which are already shippable.

- [ ] **Step 1: Verify the actual API before writing anything**

Check all three, and write what you find into the task's commit message:

```bash
# 1. Does the modifier exist in this SDK?
echo 'import SwiftUI
@available(iOS 27, *)
func probe(_ v: some View) -> some View { v.appEntityIdentifier(1) }' > /tmp/probe.swift
xcrun --sdk iphoneos swiftc -parse /tmp/probe.swift -target arm64-apple-ios27.0 2>&1 | head -5
```

2. Search the SDK headers:

```bash
grep -rl "appEntityIdentifier\|AppEntityAnnotatable" "$(xcrun --sdk iphoneos --show-sdk-path)/System/Library/Frameworks/AppIntents.framework" 2>/dev/null | head
```

3. Watch/skim WWDC26 sessions 343 ("Explore advanced App Intents features") and
   240 ("Build intelligent Siri experiences with App Schemas").

**If the API does not exist under these names, stop and report.** Ship Tasks 1–5
and revisit. Guessing at annotation APIs produces code that compiles but silently
does nothing, which is worse than not shipping the feature.

- [ ] **Step 2: Annotate item rows**

Once verified, in `ios/Wishlist/Views/ItemRow.swift` wrap the returned view:

```swift
    var body: some View {
        rowContent
            .modifier(ItemEntityAnnotation(itemID: item.id))
    }

    private var rowContent: some View {
        // ...existing HStack body, unchanged...
    }
```

Add at the bottom of the same file:

```swift
/// Tells Siri which entity a row represents, so "claim this" resolves while the
/// user is looking at it. iOS 27 only; a no-op below that, which keeps the
/// deployment target at 17.
private struct ItemEntityAnnotation: ViewModifier {
    let itemID: Int

    func body(content: Content) -> some View {
        if #available(iOS 27, *) {
            content.appEntityIdentifier(itemID)
        } else {
            content
        }
    }
}
```

- [ ] **Step 3: Annotate the detail screen as primary content**

In `ios/Wishlist/Views/ItemDetailView.swift`, add to the outermost `ZStack`:

```swift
        .modifier(ItemDetailActivity(itemID: current.id))
```

and at the bottom of the file:

```swift
/// Marks the detail screen as the primary on-screen content so Siri can resolve
/// "this" to the item being viewed.
private struct ItemDetailActivity: ViewModifier {
    let itemID: Int

    func body(content: Content) -> some View {
        if #available(iOS 27, *) {
            content.userActivity("com.reitz.wishlist.viewingItem") { activity in
                activity.title = "Viewing wishlist item"
                activity.userInfo = ["itemID": itemID]
            }
        } else {
            content
        }
    }
}
```

- [ ] **Step 4: Build for both floors**

```bash
xcodebuild -project ios/Wishlist.xcodeproj -scheme Wishlist -destination 'platform=iOS Simulator,name=iPhone 17' build 2>&1 | grep -E "BUILD (SUCCEEDED|FAILED)|error:"
```
Expected: `BUILD SUCCEEDED`, with **no** change to `deploymentTarget` in
`ios/project.yml` — confirm with `grep -A1 deploymentTarget ios/project.yml`
(must still read `iOS: "17.0"`).

- [ ] **Step 5: Smoke-test on the iOS 27 runtime**

An iOS 27 simulator runtime is installed (`27.0 24A5390f`). Create a device if
needed, install, open a member's item list, and confirm the app behaves normally
— annotations must not alter layout or interaction. Siri resolution itself cannot
be asserted here; note in the commit that it is unverified.

- [ ] **Step 6: Commit**

Substitute the real text for `REPLACE_WITH_STEP_1_FINDINGS` — do not commit the
token literally.

```bash
git add ios/Wishlist/Views
git commit -m "feat(ios): on-screen awareness annotations for Siri (iOS 27)

API verification result: REPLACE_WITH_STEP_1_FINDINGS.
Gated behind @available(iOS 27, *); deployment target stays 17.0.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Documentation and full verification

**Files:**
- Modify: `ios/README.md`

- [ ] **Step 1: Document the intents**

Add a `## Siri and App Intents` section to `ios/README.md` covering: the phrases
that work, which intents conform to `.system.search` / `.system.open` and why
add/claim are custom, that `IntentService.shared` must be configured at launch,
and that **intents are device-only** because they read the shared Keychain — in
the simulator every intent correctly reports "Open Wishlist and log in first."

- [ ] **Step 2: Run the whole suite and both builds**

```bash
export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
xcodebuild -project ios/Wishlist.xcodeproj -scheme WishlistKit -destination 'platform=iOS Simulator,name=iPhone 17' test 2>&1 | grep -E "Executed [0-9]+ tests, with|TEST (SUCCEEDED|FAILED)"
xcodebuild -project ios/Wishlist.xcodeproj -scheme Wishlist -destination 'platform=iOS Simulator,name=iPhone 17' build 2>&1 | grep -E "BUILD (SUCCEEDED|FAILED)"
xcodebuild -project ios/Wishlist.xcodeproj -scheme ShareExtension -destination 'platform=iOS Simulator,name=iPhone 17' build 2>&1 | grep -E "BUILD (SUCCEEDED|FAILED)"
```
Expected: all three succeed, ~57 tests.

- [ ] **Step 3: Commit**

```bash
git add ios/README.md
git commit -m "docs(ios): document the Siri intents and their device-only constraint

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## After this plan

Real verification needs a signed build on an iPhone: intents read the shared
Keychain, so the simulator can only prove they fail gracefully. On device, check
that "Add AirPods to my wishlist" creates an item, that search surfaces items in
Spotlight, and — on iOS 27 — that "claim this" resolves while viewing an item.
