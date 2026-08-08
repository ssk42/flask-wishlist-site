import Foundation
import UserNotifications
import UIKit
import WishlistKit

/// Owns notification permission, APNs registration, and notification taps.
/// The APNs device token is posted to /api/v1/devices so the server can push.
@MainActor
final class PushManager: NSObject, UNUserNotificationCenterDelegate {
    static let shared = PushManager()

    /// Deep-link payload from the most recently tapped notification ("link"/item).
    /// RootTabView observes this via NotificationCenter to switch tabs.
    static let openLinkNotification = Notification.Name("WishlistOpenLink")

    private override init() { super.init() }

    func start() {
        UNUserNotificationCenter.current().delegate = self
    }

    /// Call after a successful login: ask permission, then register with APNs.
    func requestAuthorization() {
        Task {
            let center = UNUserNotificationCenter.current()
            let granted = (try? await center.requestAuthorization(options: [.alert, .badge, .sound])) ?? false
            if granted {
                UIApplication.shared.registerForRemoteNotifications()
            }
        }
    }

    /// Called from the AppDelegate with the raw APNs token.
    func deviceTokenReceived(_ deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        Task { try? await AppEnvironment.client.registerDevice(apnsToken: token) }
    }

    // MARK: UNUserNotificationCenterDelegate

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter,
                                            willPresent notification: UNNotification) async
        -> UNNotificationPresentationOptions {
        [.banner, .sound, .badge]
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter,
                                            didReceive response: UNNotificationResponse) async {
        let link = response.notification.request.content.userInfo["link"] as? String
        await MainActor.run {
            NotificationCenter.default.post(name: Self.openLinkNotification, object: nil,
                                            userInfo: ["link": link ?? ""])
        }
    }
}
