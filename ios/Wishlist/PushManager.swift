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
    /// @spec IOS-ACT-006
    static let openLinkNotification = Notification.Name("WishlistOpenLink")

    private override init() { super.init() }

    func start() {
        UNUserNotificationCenter.current().delegate = self
    }

    /// Call after a successful login: ask permission (once per install — the OS
    /// only ever prompts from `.notDetermined`), then register with APNs.
    /// @spec IOS-ACT-004
    func requestAuthorization() {
        // @spec IOS-ACT-009
        Task {
            let center = UNUserNotificationCenter.current()
            let settings = await center.notificationSettings()
            switch PushPermissionPolicy.action(for: settings.authorizationStatus) {
            case .requestAndRegister:
                let granted = (try? await center.requestAuthorization(options: [.alert, .badge, .sound])) ?? false
                if granted {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            case .register:
                UIApplication.shared.registerForRemoteNotifications()
            case .skip:
                break
            }
        }
    }

    /// Called from the AppDelegate with the raw APNs token.
    func deviceTokenReceived(_ deviceToken: Data) {
        // @spec IOS-ACT-005
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        Task {
            do {
                try await AppEnvironment.client.registerDevice(apnsToken: token)
            } catch {
                // Push won't work until this lands; log it rather than silently
                // swallowing (a permission change or retry by the user re-triggers).
                print("Device registration failed: \(error)")
            }
        }
    }

    /// Mirror the unread notification count on the app icon (capped at 99).
    /// Callers: ActivityView after load / mark-all-read, and app foreground sync.
    /// @spec IOS-ACT-010
    func syncBadge(unreadCount: Int) {
        UIApplication.shared.applicationIconBadgeNumber = Badge.value(unreadCount: unreadCount)
    }

    // MARK: UNUserNotificationCenterDelegate

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter,
                                            willPresent notification: UNNotification) async
        -> UNNotificationPresentationOptions {
        // @spec IOS-ACT-007
        [.banner, .sound, .badge]
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter,
                                            didReceive response: UNNotificationResponse) async {
        // @spec IOS-ACT-006
        let link = response.notification.request.content.userInfo["link"] as? String
        await MainActor.run {
            UIApplication.shared.applicationIconBadgeNumber = 0  // the user just saw it
            NotificationCenter.default.post(name: Self.openLinkNotification, object: nil,
                                            userInfo: ["link": link ?? ""])
        }
    }
}
