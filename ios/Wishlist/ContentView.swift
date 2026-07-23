import SwiftUI
import WishlistKit

struct ContentView: View {
    let session: Session

    var body: some View {
        switch session.state {
        case .loggedOut:
            LoginView(session: session)
        case .loggedIn:
            RootTabView(session: session)
        }
    }
}

/// Placeholder root; the real tab bar lands in Task 8.
struct RootTabView: View {
    let session: Session

    var body: some View {
        VStack(spacing: 16) {
            Text("Signed in")
            Button("Log out") { Task { await session.logOut() } }
        }
    }
}
