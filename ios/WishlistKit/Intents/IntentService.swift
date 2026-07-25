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
