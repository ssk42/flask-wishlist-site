# ios-share LLD

## Context and Design Philosophy

`ios-share` is the Safari Share-extension target: from the share sheet, a user
shares a product URL, the extension prefills an item draft (title → description,
price, image) via the metadata endpoint, lets the user edit, and posts it to their
own wishlist. It is a **separate process** that links `WishlistKit` (`embed: false`)
and authenticates with the bearer token the main app stored in the shared Keychain
access group — hence no login UI; if the token is absent or 401s, the extension
tells the user to open the app.

## Core Components

### `ShareViewController` — `ios/ShareExtension/ShareViewController.swift`
Hosts the SwiftUI `ShareView`. On `viewDidLoad`, calls `present()`:
1. `sharedURL()` extracts a `public.url` or a plain-text HTTP URL from the
   `NSExtensionItem` attachments (:69-90); returns `nil` (→ cancel) if nothing
   usable.
2. Builds `KeychainTokenStore(accessGroup: WishlistAPI.sharedKeychainGroup)`,
   `APIClient(baseURL: WishlistAPI.defaultBaseURL, tokenProvider: { store.read() })`,
   and a `ShareItemViewModel`.
3. Hosts `ShareView` and wires `onFinished`/`onCancel` to `completeRequest` /
   `cancelRequest` (:47-66).
`loadString` reduces the non-`Sendable` loaded item to a String *inside* the
completion handler via a continuation (:92-109).

### `ShareView` — `ios/ShareExtension/ShareView.swift`
Form: description (multi-line), price (decimal), priority Picker (default Medium).
The shared URL shown as a caption footer. `ProgressView` + "Looking up details…"
while prefilling; error text when `vm.error` set. Save disabled unless
`vm.canSubmit && !saving && !vm.needsLogin`. `.task` triggers `vm.prefill`, then
seeds price text. Carries its own `wlShareBg` color (the app target's
`Theme.swift` is not linked into the extension process).

### `ShareItemViewModel` — `ios/WishlistKit/ViewModels/ShareItemViewModel.swift`
- `draft` is a **public var** (user-editable, :9); `prefill(urlString:)` (:20-38)
  always sets `draft.link = urlString` first, then `client.fetchMetadata`
  best-effort — description only if non-empty, plus price/imageURL; metadata
  failure stays silent except `APIError.unauthorized` → `needsLogin = true`.
- `canSubmit` = non-empty trimmed description (:41-43).
- `submit() -> Bool` (:46-62): `client.createItem(draft)`, sets `needsLogin` on
  401, validation message on 400, generic "Couldn't save. Try again." otherwise.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| `[inferred]` No login UI in the extension | Reuse shared-group token | Own login flow | The app wrote the token to the shared Keychain group; a separate login is redundant and confusing. |
| `[inferred]` Metadata prefill is best-effort + silent | Partial prefill | Block on metadata | The user can always edit/submit even if lookup fails; link is always kept. |
| `[inferred]` URL extracted from `public.url` OR plain text | Both attempt | URL-only | Safari shares `public.url`, some apps share plain text. |
| `[inferred]` Extension carries its own `wlShareBg` | Duplicated one color | Link app Theme | Theme lives in the app target, not linked into the extension; impossible to share without moving design tokens into WishlistKit. |
| `[inferred]` Non-`Sendable` item reduced to String in the completion handler | Continuation with String | Pass item across | Only a String is `Sendable`; crosses the continuation safely. |

## Open Questions & Future Decisions

### Resolved
1. ✅ Authenticated save is only verifiable on a signed device build — the
   simulator cannot write the shared Keychain group, so the extension always
   reports "open the app and log in" there (README documents this).

### Deferred
1. Design tokens (the cream background) are duplicated in the extension because
   `Theme.swift` lives in the app target — extract shared tokens into WishlistKit
   so the extension matches the full palette.
2. Only one color is carried today; if the extension grows more UI, the duplication
   will force the WishlistKit extraction.

## References

- `docs/intent/boundary-ios/ios-share/ios-share-specs.md`
- Tests: `ios/WishlistKitTests/ShareItemViewModelTests.swift`
- Code: `ios/ShareExtension/ShareViewController.swift`, `ios/ShareExtension/ShareView.swift`,
  `ios/ShareExtension/ShareExtension.entitlements`, `ios/ShareExtension/Info.plist`,
  `ios/WishlistKit/ViewModels/ShareItemViewModel.swift`