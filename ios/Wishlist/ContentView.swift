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
