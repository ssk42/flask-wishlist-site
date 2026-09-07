import SwiftUI
import WishlistKit

/// Root tab bar: Family, My List, Claims, Activity, Events. A tapped push notification
/// deep-links — /items/<id> presents the item detail (own items → My List tab),
/// /events/<id> switches to the Events tab and presents that event's detail,
/// any other link switches to the Activity tab.
struct RootTabView: View {
    let session: Session
    @State private var selectedTab = 0
    private let openTarget = OpenTarget.shared
    @State private var deepLinkTarget: ItemDetail?
    @State private var deepLinkError = false

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

            EventsView(session: session)
                .tabItem { Label("Events", systemImage: "calendar") }
                .tag(4)
        }
        .tint(.wlAccent)
        .fullScreenCover(item: $deepLinkTarget) { target in
            DeepLinkDetailView(client: session.client, detail: target)
        }
        .alert("Item not found", isPresented: $deepLinkError) {
            Button("OK", role: .cancel) { selectedTab = 3 }
        } message: {
            Text("That item may have been removed.")
        }
        // A tapped push notification deep-links: /items/<id> → the item detail
        // (own items → My List tab); /events/<id> → the Events tab + that
        // event's detail; any other link → Activity tab.
        .onReceive(NotificationCenter.default.publisher(for: PushManager.openLinkNotification)) { note in
            let link = (note.userInfo?["link"] as? String) ?? ""
            route(link: link)
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

    private func route(link: String) {
        // @spec IOS-ACT-008
        // @spec IOS-EVT-013 — event links share `ItemLink` with the in-app
        // tap path, so push and in-app routing can never drift. The detail
        // itself is presented by `EventsView`, which consumes the pending id
        // once its list has loaded (mirroring `OpenTarget.pendingOwnerID`).
        if let eventID = ItemLink.eventID(from: link) {
            openTarget.setPendingEvent(id: eventID)
            selectedTab = 4
            return
        }
        guard let itemID = ItemLink.itemID(from: link) else {
            selectedTab = 3
            return
        }
        Task { await openItem(id: itemID) }
    }

    private func openItem(id: Int) async {
        let detail: ItemDetail
        do {
            detail = try await session.client.item(id: id)
        } catch {
            deepLinkError = true
            return
        }
        // Own item → My List tab (its claim state is hidden by surprise protection).
        if detail.item.isOwn {
            selectedTab = 1
            return
        }
        deepLinkTarget = detail
    }
}