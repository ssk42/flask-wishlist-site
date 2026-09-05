import Foundation
import Observation

@MainActor @Observable
public final class MyListViewModel {
    public var query = ""
    /// nil = All for each filter. A nil item field matches only All.
    public var selectedPriority: String?
    public var selectedCategory: String?
    /// @spec IOS-CUR-009, IOS-CUR-011
    public var filteredItems: [Item] {
        items.filter { item in
            (TextSearch.matches(item.description, query: query)
                || (item.category.map { TextSearch.matches($0, query: query) } ?? false))
                && (selectedPriority.map { item.priority == $0 } ?? true)
                && (selectedCategory.map { item.category == $0 } ?? true)
        }
    }

    public private(set) var items: [Item] = []
    public private(set) var error: String?
    public var isLoading = false
    private let client: APIClient
    private let userID: Int

    public init(client: APIClient, userID: Int) {
        self.client = client
        self.userID = userID
    }

    /// @spec IOS-CUR-010
    public static func userID(from state: SessionState) -> Int? {
        if case .loggedIn(let u) = state { return u.id }
        return nil
    }

    public func load() async {
        // @spec IOS-CUR-001
        isLoading = true
        error = nil
        do { items = try await client.items(userID: userID) }
        catch { self.error = "Couldn't load your list." }
        isLoading = false
    }

    @discardableResult
    public func create(_ draft: ItemDraft) async -> Bool {
        // @spec IOS-CUR-002
        error = nil
        do {
            let item = try await client.createItem(draft)
            items.insert(item, at: 0)
            return true
        } catch let APIError.validation(messages) {
            self.error = messages.first ?? "Please check the fields."
            return false
        } catch {
            self.error = "Couldn't add item."
            return false
        }
    }

    @discardableResult
    public func update(id: Int, _ patch: ItemDraft) async -> Bool {
        // @spec IOS-CUR-003
        error = nil
        do {
            let updated = try await client.updateItem(id: id, patch)
            if let i = items.firstIndex(where: { $0.id == id }) { items[i] = updated }
            return true
        } catch let APIError.validation(messages) {
            self.error = messages.first ?? "Please check the fields."
            return false
        } catch {
            self.error = "Couldn't save changes."
            return false
        }
    }

    public func delete(_ item: Item) async {
        // @spec IOS-CUR-004
        error = nil
        do {
            try await client.deleteItem(id: item.id)
            items.removeAll { $0.id == item.id }
        } catch {
            self.error = "Couldn't delete item."
        }
    }

    /// Best-effort metadata prefill for the add/edit form. Always returns a draft
    /// whose `link` is the given URL (never loses what the user typed); server
    /// fields (description/price/image) are filled when the lookup succeeds.
    /// @spec IOS-CUR-008
    public func prefill(url: String) async -> ItemDraft {
        (try? await client.fetchMetadata(url: url)) ?? ItemDraft(link: url)
    }
}