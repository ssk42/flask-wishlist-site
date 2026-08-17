import Foundation
import Observation

/// @spec IOS-AUTH-001
public enum SessionState: Sendable, Equatable {
    case loggedOut
    case loggedIn(User)
}

@MainActor @Observable
public final class Session {
    // @spec IOS-AUTH-001
    public private(set) var state: SessionState = .loggedOut
    public let client: APIClient
    private let tokenStore: TokenStoring

    public init(client: APIClient, tokenStore: TokenStoring) {
        self.client = client
        self.tokenStore = tokenStore
    }

    /// A stored token implies a prior successful login. Restore the session by
    /// fetching the current user: a live token becomes `.loggedIn(user)`, a
    /// revoked/expired one (401) clears the token and stays `.loggedOut`. With no
    /// stored token this is a no-op.
    /// @spec IOS-AUTH-007
    public func bootstrap() async {
        guard tokenStore.read() != nil else { return }
        do {
            let user = try await client.me()
            state = .loggedIn(user)
        } catch APIError.unauthorized {
            tokenStore.clear()
        } catch {
            // Transient network failure: don't clear a valid token or log the
            // user out; stay loggedOut and let a fresh launch retry.
        }
    }

    @discardableResult
    public func logIn(email: String, familyCode: String) async -> Bool {
        // @spec IOS-AUTH-002
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
        // @spec IOS-AUTH-003
        try? await client.logout()
        tokenStore.clear()
        state = .loggedOut
    }
}
