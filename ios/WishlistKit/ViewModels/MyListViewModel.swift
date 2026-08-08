import Foundation
import Observation

@MainActor @Observable
public final class MyListViewModel {
    public private(set) var items: [Item] = []
    public private(set) var error: String?
    public var isLoading = false
    private let client: APIClient
    private let userID: Int

    public init(client: APIClient, userID: Int) {
        self.client = client
        self.userID = userID
    }

    public func load() async {
        isLoading = true
        error = nil
        do { items = try await client.items(userID: userID) }
        catch { self.error = "Couldn't load your list." }
        isLoading = false
    }

    @discardableResult
    public func create(_ draft: ItemDraft) async -> Bool {
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
        error = nil
        do {
            try await client.deleteItem(id: item.id)
            items.removeAll { $0.id == item.id }
        } catch {
            self.error = "Couldn't delete item."
        }
    }
}
