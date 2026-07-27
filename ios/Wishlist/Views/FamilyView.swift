import SwiftUI
import WishlistKit

/// Path element pushed when the pending target names a specific item (e.g.
/// Siri's "open the cashmere blanket"), so `MemberItemsView` knows which one
/// to highlight. An ordinary tap on a member card pushes a bare `User`
/// instead — see the `User.self` destination below — and highlights nothing.
private struct PendingItemDestination: Hashable {
    let user: User
    let itemID: Int
}

struct FamilyView: View {
    let client: APIClient
    @State private var vm: FamilyViewModel
    @State private var path = NavigationPath()
    private let openTarget = OpenTarget.shared

    init(client: APIClient) {
        self.client = client
        _vm = State(initialValue: FamilyViewModel(client: client))
    }

    var body: some View {
        NavigationStack(path: $path) {
            ZStack {
                Color.wlBg.ignoresSafeArea()
                Group {
                    if vm.isLoading && vm.users.isEmpty {
                        ProgressView().tint(.wlAccent)
                    } else if let error = vm.error, vm.users.isEmpty {
                        ContentUnavailableView("Couldn't load", systemImage: "wifi.slash",
                                               description: Text(error))
                    } else {
                        ScrollView {
                            WLScreenTitle("Family")
                            LazyVStack(spacing: 12) {
                                ForEach(vm.users) { user in
                                    NavigationLink(value: user) { memberCard(user) }
                                        .buttonStyle(WLCardButtonStyle())
                                }
                            }
                            .padding(.horizontal, 18)
                        }
                        .refreshable { await vm.load() }
                    }
                }
            }
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: User.self) { user in
                MemberItemsView(client: client, member: user)
            }
            .navigationDestination(for: PendingItemDestination.self) { destination in
                MemberItemsView(client: client, member: destination.user, highlightItemID: destination.itemID)
            }
        }
        .tint(.wlAccent)
        .task {
            if vm.users.isEmpty { await vm.load() }
            navigateToPendingOwnerIfPossible()
        }
        // Handles both: a target that arrives while this view is already on
        // screen (warm case, users already loaded), and a target that was
        // pending before `vm.users` finished loading (cold case) — either can
        // flip after the `.task` above has already run once.
        .onChange(of: vm.users) { _, _ in navigateToPendingOwnerIfPossible() }
        .onChange(of: openTarget.pendingOwnerID) { _, _ in navigateToPendingOwnerIfPossible() }
    }

    /// Pushes to the pending owner's item list once both the target and the
    /// member list are available. Leaves the target untouched if the member
    /// list hasn't loaded yet — a later call (via the `onChange` above) will
    /// pick it up rather than losing it.
    ///
    /// The actual routing decision lives in `OpenTarget.resolveDestination`,
    /// a pure function tested in isolation (`OpenTargetTests`); this is just
    /// the thin binding from that decision to `NavigationPath` — set the
    /// path, then consume, only once there's somewhere to go.
    private func navigateToPendingOwnerIfPossible() {
        guard let user = openTarget.resolveDestination(in: vm.users) else { return }
        let pending = openTarget.consumePending()
        // Replace whatever's already on the stack rather than deepening it —
        // a second "open" (e.g. two Siri requests back to back) should land
        // on the new target, not stack behind whatever was already pushed.
        if !path.isEmpty { path.removeLast(path.count) }
        if let itemID = pending?.itemID {
            path.append(PendingItemDestination(user: user, itemID: itemID))
        } else {
            path.append(user)
        }
    }

    private func memberCard(_ user: User) -> some View {
        HStack(spacing: 14) {
            Monogram(name: user.name)
            VStack(alignment: .leading, spacing: 2) {
                Text(user.name)
                    .font(.body.weight(.semibold))
                    .foregroundStyle(Color.wlInk)
                Text("\(user.itemCount ?? 0) \(user.itemCount == 1 ? "item" : "items")")
                    .font(.subheadline)
                    .foregroundStyle(Color.wlSecondary)
            }
            Spacer()
            Image(systemName: "chevron.right")
                .font(.footnote.weight(.semibold))
                .foregroundStyle(Color.wlSecondary.opacity(0.6))
        }
        .wlCard()
    }
}
