import SwiftUI
import WishlistKit

struct RootTabView: View {
    let session: Session
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            FamilyView(client: session.client)
                .tabItem { Label("Family", systemImage: "person.2") }
                .tag(0)

            MyListView(session: session)
                .tabItem { Label("My List", systemImage: "list.bullet") }
                .tag(1)

            ClaimsView(client: session.client)
                .tabItem { Label("Claims", systemImage: "gift") }
                .tag(2)

            ActivityView(client: session.client)
                .tabItem { Label("Activity", systemImage: "bell") }
                .tag(3)
        }
        .tint(.wlAccent)
        // Tapping a push notification deep-links to the Activity tab.
        .onReceive(NotificationCenter.default.publisher(for: PushManager.openLinkNotification)) { _ in
            selectedTab = 3
        }
    }
}
