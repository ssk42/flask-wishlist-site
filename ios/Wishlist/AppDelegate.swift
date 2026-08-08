import UIKit

final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        // Must be first: App Intents can be instantiated and executed by the
        // system at any point after launch, and IntentService.shared has no
        // token until this runs. Anything that awaits before this line risks
        // an intent firing against the placeholder, signed-out service.
        AppEnvironment.configureIntents()
        Task { @MainActor in PushManager.shared.start() }
        return true
    }

    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        Task { @MainActor in PushManager.shared.deviceTokenReceived(deviceToken) }
    }

    func application(_ application: UIApplication,
                     didFailToRegisterForRemoteNotificationsWithError error: Error) {
        // Expected on the simulator (no real APNs); nothing to do.
        print("APNs registration failed: \(error.localizedDescription)")
    }
}
