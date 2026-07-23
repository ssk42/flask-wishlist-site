import SwiftUI
import WishlistKit

struct RootTabView: View {
    let session: Session

    var body: some View {
        TabView {
            FamilyView(client: session.client)
                .tabItem { Label("Family", systemImage: "person.2") }

            MyListView(session: session)
                .tabItem { Label("My List", systemImage: "list.bullet") }

            ClaimsView(client: session.client)
                .tabItem { Label("Claims", systemImage: "gift") }

            ActivityView(client: session.client)
                .tabItem { Label("Activity", systemImage: "bell") }
        }
    }
}
