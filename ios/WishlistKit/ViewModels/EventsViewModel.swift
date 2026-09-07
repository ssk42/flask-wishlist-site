import Foundation
import Observation

@MainActor @Observable
public final class EventsViewModel {
    public private(set) var upcoming: [WishlistEvent] = []
    public private(set) var past: [WishlistEvent] = []
    public private(set) var error: String?
    public var isLoading = false
    private let client: APIClient

    public init(client: APIClient) { self.client = client }

    public func load() async {
        // @spec IOS-EVT-001, IOS-EVT-004
        isLoading = true
        error = nil
        do {
            let events = try await client.events()
            upcoming = events.filter(\.isUpcoming).sorted { $0.date < $1.date }
            past = events.filter { !$0.isUpcoming }.sorted { $0.date > $1.date }
        } catch {
            self.error = "Couldn't load events."
        }
        isLoading = false
    }

    @discardableResult
    public func create(name: String, date: Date) async -> Bool {
        // @spec IOS-EVT-006, IOS-EVT-010
        error = nil
        do {
            insert(try await client.createEvent(name: name, date: date))
            return true
        } catch let APIError.validation(messages) {
            self.error = messages.first ?? "Please check the fields."
            return false
        } catch {
            self.error = "Couldn't create event."
            return false
        }
    }

    @discardableResult
    public func update(id: Int, name: String, date: Date) async -> Bool {
        // @spec IOS-EVT-007, IOS-EVT-010
        error = nil
        do {
            replace(try await client.updateEvent(id: id, name: name, date: date))
            return true
        } catch let APIError.validation(messages) {
            self.error = messages.first ?? "Please check the fields."
            return false
        } catch let APIError.http(status, _) where status == 403 {
            await load()
            self.error = "You can only edit events you created."
            return false
        } catch let APIError.http(status, _) where status == 404 {
            await load()
            self.error = "That event no longer exists."
            return false
        } catch {
            self.error = "Couldn't save changes."
            return false
        }
    }

    public func delete(_ event: WishlistEvent) async {
        // @spec IOS-EVT-008, IOS-EVT-010
        error = nil
        do {
            try await client.deleteEvent(id: event.id)
            remove(id: event.id)
        } catch let APIError.http(status, _) where status == 403 {
            await load()
            self.error = "You can only delete events you created."
        } catch let APIError.http(status, _) where status == 404 {
            await load()
            self.error = "That event no longer exists."
        } catch {
            self.error = "Couldn't delete event."
        }
    }

    /// Inserts into upcoming/past by device-calendar day, keeping sort order.
    /// @spec IOS-EVT-006
    private func insert(_ event: WishlistEvent) {
        if event.isUpcoming {
            upcoming.append(event)
            upcoming.sort { $0.date < $1.date }
        } else {
            past.append(event)
            past.sort { $0.date > $1.date }
        }
    }

    /// Full-replace semantics: the server's copy is authoritative, so drop the
    /// stale row and re-insert (a date edit may move partitions).
    /// @spec IOS-EVT-007
    private func replace(_ event: WishlistEvent) {
        remove(id: event.id)
        insert(event)
    }

    /// @spec IOS-EVT-008
    private func remove(id: Int) {
        upcoming.removeAll { $0.id == id }
        past.removeAll { $0.id == id }
    }
}
