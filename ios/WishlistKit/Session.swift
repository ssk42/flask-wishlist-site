import Foundation
import Observation

public enum SessionState: Sendable, Equatable {
    case loggedOut
    case loggedIn(User)
}

@MainActor @Observable
public final class Session {
    public private(set) var state: SessionState = .loggedOut
    public let client: APIClient
    private let tokenStore: TokenStoring

    public init(client: APIClient, tokenStore: TokenStoring) {
        self.client = client
        self.tokenStore = tokenStore
    }

    /// A stored token implies a prior successful login; the first API call that
    /// returns 401 bounces back to loggedOut. v1 keeps it simple: token presence
    /// alone does not restore the cached User, so we stay loggedOut until an
    /// explicit login provides the user object.
    public func bootstrap() {}

    @discardableResult
    public func logIn(email: String, familyCode: String) async -> Bool {
        do {
            let result = try await client.login(email: email, familyCode: familyCode)
            tokenStore.save(result.token)
            state = .loggedIn(result.user)
            return true
        } catch {
            return false
        }
    }

    public func logOut() async {
        try? await client.logout()
        tokenStore.clear()
        state = .loggedOut
    }
}
