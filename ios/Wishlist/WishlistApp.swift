import SwiftUI
import WishlistKit

@main
struct WishlistApp: App {
    @State private var session = AppEnvironment.makeSession()

    var body: some Scene {
        WindowGroup {
            ContentView(session: session)
        }
    }
}
