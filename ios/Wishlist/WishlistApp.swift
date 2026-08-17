import SwiftUI
import WishlistKit

@main
struct WishlistApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @State private var session = AppEnvironment.makeSession()

    var body: some Scene {
        WindowGroup {
            ContentView(session: session)
                .task { await session.bootstrap() }
                .onChange(of: session.state) { _, newState in
                    // @spec IOS-ACT-004
                    // First successful login → ask for push permission + register.
                    if case .loggedIn = newState {
                        PushManager.shared.requestAuthorization()
                    }
                }
        }
    }
}
