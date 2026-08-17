# ios-share EARS Specifications

- `[x]` **IOS-SHARE-001**: When the share extension receives a share sheet request,
  the system shall extract a URL from a `public.url` attachment, or from the first
  HTTP-prefixed token of a plain-text attachment, and shall cancel (close) if
  neither is present.
- `[x]` **IOS-SHARE-002**: The system shall always set the draft's `link` to the
  shared URL first, then best-effort prefill description/price/image from the
  metadata endpoint without blocking submission if lookup fails.
- `[x]` **IOS-SHARE-003**: The extension shall allow submission only when the
  description is non-empty, and shall post the completed draft to create an item.
- `[x]` **IOS-SHARE-004**: The extension shall authenticate with the bearer token
  the main app stored in the shared Keychain access group; when no token is
  available or a request returns 401, it shall surface a "open the app and log in"
  state rather than showing login UI.
- `[x]` **IOS-SHARE-005**: On a 400 validation response, the extension shall surface
  the server's validation message; on other failures, a generic save error.