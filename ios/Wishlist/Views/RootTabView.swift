import SwiftUI
import WishlistKit

struct RootTabView: View {
    let session: Session
    @State private var selectedTab = 0
    private let openTarget = OpenTarget.shared

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
        // Siri "open this item" deep-links to the Family tab. The notification
        // itself carries no payload — the target lives in `OpenTarget`, which
        // `FamilyView` reads to actually push to the owner's item list.
        .onReceive(NotificationCenter.default.publisher(for: .wishlistOpenItem)) { _ in
            switchToFamilyTabIfTargetPending()
        }
        // Cold launch: the intent may have set a pending target before this
        // view ever existed, so the notification above was posted into a void
        // and lost. Checking again on appear picks up that stale-but-still-
        // valid target instead of silently dropping it.
        .onAppear {
            switchToFamilyTabIfTargetPending()
        }
    }

    private func switchToFamilyTabIfTargetPending() {
        if openTarget.pendingOwnerID != nil {
            selectedTab = 0
        }
    }
}
