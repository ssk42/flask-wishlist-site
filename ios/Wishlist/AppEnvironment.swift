import Foundation
import WishlistKit

/// Wires the real app dependencies (Keychain token store + API client pointed at
/// the backend). The base URL defaults to the local Flask server for
/// simulator-against-local development; swap for the Heroku URL to ship.
///
/// `tokenStore` and `client` are `Sendable` and deliberately non-isolated so the
/// client's `@Sendable` token provider can read the token from any context; only
/// `makeSession()` is main-actor isolated, since `Session` is `@MainActor`.
enum AppEnvironment {
    static let tokenStore = KeychainTokenStore()
    static let client = APIClient(
        baseURL: URL(string: "http://localhost:5000")!,
        tokenProvider: { tokenStore.read() }
    )

    @MainActor
    static func makeSession() -> Session { Session(client: client, tokenStore: tokenStore) }
}
