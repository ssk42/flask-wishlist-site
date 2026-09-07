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
}
