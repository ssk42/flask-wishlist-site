import Foundation
import Observation

@MainActor @Observable
public final class ActivityViewModel {
    public private(set) var notifications: [WishlistNotification] = []
    public private(set) var unreadCount = 0
    public private(set) var error: String?
    public var isLoading = false
    private let client: APIClient

    public init(client: APIClient) { self.client = client }

    public func load() async {
        isLoading = true
        error = nil
        do {
            let result = try await client.notifications()
            notifications = result.items
            unreadCount = result.unreadCount
        } catch {
            self.error = "Couldn't load activity."
        }
        isLoading = false
    }

    public func markRead(_ notification: WishlistNotification) async {
        guard !notification.isRead else { return }
        do {
            try await client.markNotificationRead(id: notification.id)
            await load()
        } catch {
            self.error = "Couldn't mark as read."
        }
    }

    public func markAllRead() async {
        do {
            try await client.markAllNotificationsRead()
            await load()
        } catch {
            self.error = "Couldn't mark all read."
        }
    }
}
