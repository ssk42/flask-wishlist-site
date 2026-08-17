---
status: OK
---

# ios-networking Arrow

The shared `WishlistKit` networking + model layer: the `APIClient` actor against
`/api/v1`, the Codable models (with surprise-protection-optional `Item.status`),
`ItemDraft`, and the base-URL resolution.

## Artifacts
- **LLD**: [docs/intent/boundary-ios/ios-networking.md](../../intent/boundary-ios/ios-networking.md)
- **EARS Specs**: [docs/intent/boundary-ios/ios-networking/ios-networking-specs.md](../../intent/boundary-ios/ios-networking/ios-networking-specs.md)
- **Tests**: `ios/WishlistKitTests/APIClientTests.swift`,
  `ios/WishlistKitTests/APIClientReadTests.swift`,
  `ios/WishlistKitTests/APIClientWriteTests.swift`,
  `ios/WishlistKitTests/ModelDecodingTests.swift`,
  `ios/WishlistKitTests/WishlistAPITests.swift`,
  `ios/WishlistKitTests/Support/StubURLProtocol.swift`
- **Code** (client): `ios/WishlistKit/Networking/*.swift`, `ios/WishlistKit/Models/*.swift`,
  `ios/WishlistKit/WishlistAPI.swift`, `ios/WishlistKit/WishlistKit.h`
- **Code** (server — the `/api/v1` surface this client consumes):
  `blueprints/api_v1.py`, `services/api_auth.py`, `services/api_serializers.py`,
  `services/push_service.py`

## Spec Coverage

| Category | Spec IDs | Implemented | Deferred | Gaps |
|----------|----------|-------------|----------|------|
| Core     | IOS-NET-001 to IOS-NET-013 | 13 | 0 | 0 |

**Summary:** 13 of 13 active specs implemented.

## Key Findings

1. **Surprise protection is typed, not checked** — `Item.status`/`lastUpdatedBy` are
   Optional and `isOwn` derives from `status == nil` (`Item.swift:35`); the client
   never re-adds claim state for own items.
2. **URL building uses `URL(string:relativeTo:)`** to avoid the leading-slash
   percent-encoding bug in `appendingPathComponent` (`APIClient.swift:124-131`).
3. **Base URL defaults to the deployed host** (`WishlistAPI.swift:7`) with
   `WLAPIBaseURL` plist override — the `AppEnvironment` "local server" comment is stale.
4. **`Placeholder.swift` is vestigial** — pre-real-code marker enum, deletion candidate.
5. **`fetchMetadata` decodes a typed `MetadataEnvelope`** — no JSONSerialization
   double-parse; nil-filtering is consolidated to `sendRaw`'s single
   `compactMapValues`.

## Work Required

### Nice to Have
1. Confirm `unregisterDevice` token embeds safely in the URL path.
2. Delete `ios/WishlistKit/Placeholder.swift`.