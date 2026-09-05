import Foundation
import Observation

@MainActor @Observable
public final class MemberItemsViewModel {
    public let member: User
    public private(set) var items: [Item] = []
    public private(set) var error: String?
    public var isLoading = false
    private let client: APIClient

    public var query = ""
    /// nil = All for each filter. A nil item field matches only All.
    public var selectedStatus: String?
    public var selectedPriority: String?
    public var selectedCategory: String?
    /// @spec IOS-GIFT-011, IOS-GIFT-012
    public var filteredItems: [Item] {
        items.filter { item in
            (TextSearch.matches(item.description, query: query)
                || (item.category.map { TextSearch.matches($0, query: query) } ?? false))
                && (selectedStatus.map { item.status == $0 } ?? true)
                && (selectedPriority.map { item.priority == $0 } ?? true)
                && (selectedCategory.map { item.category == $0 } ?? true)
        }
    }

    public init(client: APIClient, member: User) {
        self.client = client
        self.member = member
    }

    public func load() async {
        // @spec IOS-GIFT-002
        isLoading = true
        error = nil
        do { items = try await client.items(userID: member.id) }
        catch { self.error = "Couldn't load items." }
        isLoading = false
    }

    // @spec IOS-GIFT-003
    public func claim(_ item: Item) async { await mutate(item) { try await self.client.claim(itemID: item.id) } }
    public func unclaim(_ item: Item) async { await mutate(item) { try await self.client.unclaim(itemID: item.id) } }
    public func purchase(_ item: Item) async { await mutate(item) { try await self.client.purchase(itemID: item.id) } }

    private func mutate(_ item: Item, _ action: @escaping () async throws -> Item) async {
        error = nil
        do {
            let updated = try await action()
            if let i = items.firstIndex(where: { $0.id == item.id }) { items[i] = updated }
        } catch let APIError.conflict(code) {
            self.error = friendly(code)
        } catch {
            self.error = "Action failed. Try again."
        }
    }

    // @spec IOS-GIFT-004
    private func friendly(_ code: String) -> String { ConflictCopy.friendly(code) }
}