import Foundation
import Observation

@MainActor @Observable
public final class ClaimsViewModel {
    public private(set) var items: [Item] = []
    public private(set) var error: String?
    public var isLoading = false
    private let client: APIClient

    public var query = ""
    /// nil = All, else Claimed/Purchased.
    public var selectedStatus: String?
    /// @spec IOS-GIFT-013
    public var filteredItems: [Item] {
        items.filter { item in
            (TextSearch.matches(item.description, query: query)
                || (item.category.map { TextSearch.matches($0, query: query) } ?? false))
                && (selectedStatus.map { item.status == $0 } ?? true)
        }
    }

    public init(client: APIClient) { self.client = client }

    public func load() async {
        // @spec IOS-GIFT-007
        isLoading = true
        error = nil
        do { items = try await client.myClaims() }
        catch { self.error = "Couldn't load your claims." }
        isLoading = false
    }

    public func unclaim(_ item: Item) async {
        // @spec IOS-GIFT-004, IOS-GIFT-007
        error = nil
        do {
            _ = try await client.unclaim(itemID: item.id)
            items.removeAll { $0.id == item.id }
        } catch let APIError.conflict(code) {
            self.error = ConflictCopy.friendly(code)
        } catch {
            self.error = "Couldn't unclaim."
        }
    }

    public func purchase(_ item: Item) async {
        // @spec IOS-GIFT-004, IOS-GIFT-007
        error = nil
        do {
            let updated = try await client.purchase(itemID: item.id)
            if let i = items.firstIndex(where: { $0.id == item.id }) { items[i] = updated }
        } catch let APIError.conflict(code) {
            self.error = ConflictCopy.friendly(code)
        } catch {
            self.error = "Couldn't mark purchased."
        }
    }
}