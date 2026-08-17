import Foundation
import Observation

@MainActor @Observable
public final class FamilyViewModel {
    public private(set) var users: [User] = []
    public private(set) var error: String?
    public var isLoading = false
    private let client: APIClient

    public init(client: APIClient) { self.client = client }

    public func load() async {
        // @spec IOS-GIFT-001
        isLoading = true
        error = nil
        do { users = try await client.users() }
        catch { self.error = "Couldn't load family. Pull to refresh." }
        isLoading = false
    }
}
