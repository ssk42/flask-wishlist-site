import SwiftUI
import WishlistKit

struct MemberItemsView: View {
    let client: APIClient
    @State private var vm: MemberItemsViewModel
    /// The item Siri (or a deep link) asked to open, if any. A plain `let`,
    /// deliberately not an `init`-seeded `@State`: SwiftUI may reuse this view
    /// for a new path value, and seeded state would keep the previous request's
    /// answer. The highlight below is derived from this rather than stored.
    let highlightItemID: Int?
    /// Which row is currently outlined. One-shot focus affordance, not
    /// persistent state — set when the item is revealed, cleared 1.5s later.
    @State private var highlightedItemID: Int?

    init(client: APIClient, member: User, highlightItemID: Int? = nil) {
        self.client = client
        self.highlightItemID = highlightItemID
        _vm = State(initialValue: MemberItemsViewModel(client: client, member: member))
    }

    var body: some View {
        ZStack {
            Color.wlBg.ignoresSafeArea()
            if vm.items.isEmpty && !vm.isLoading {
                ContentUnavailableView("No items yet", systemImage: "gift")
            } else {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            if let error = vm.error {
                                Text(error).font(.footnote).foregroundStyle(Color.wlAccent)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            ForEach(vm.items) { item in
                                NavigationLink(value: item) {
                                    HStack {
                                        ItemRow(item: item)
                                        Image(systemName: "chevron.right")
                                            .font(.footnote.weight(.semibold))
                                            .foregroundStyle(Color.wlSecondary.opacity(0.5))
                                    }
                                    .wlCard()
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                                            .strokeBorder(Color.wlAccent, lineWidth: highlightedItemID == item.id ? 2 : 0)
                                    )
                                }
                                .buttonStyle(WLCardButtonStyle())
                                .id(item.id)
                            }
                        }
                        .animation(.easeOut(duration: 0.3), value: highlightedItemID)
                        .padding(.horizontal, 18).padding(.top, 8)
                    }
                    .refreshable { await vm.load() }
                    .task(id: vm.items) {
                        await revealHighlightIfNeeded(proxy: proxy)
                    }
                }
            }
        }
        .navigationTitle(vm.member.name)
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: Item.self) { item in
            ItemDetailView(item: item, vm: vm)
        }
        .task { if vm.items.isEmpty { await vm.load() } }
    }

    /// Scrolls to and briefly outlines the requested item once it's actually
    /// in the loaded list. If the id never shows up — unknown id, or this
    /// member simply doesn't have that item — this degrades silently to the
    /// plain list: no scroll, no highlight, no error.
    private func revealHighlightIfNeeded(proxy: ScrollViewProxy) async {
        guard let id = highlightItemID, vm.items.contains(where: { $0.id == id }) else { return }
        highlightedItemID = id
        withAnimation { proxy.scrollTo(id, anchor: .center) }
        try? await Task.sleep(for: .seconds(1.5))
        // A refresh or mutation mid-window cancels this task and starts a new
        // one. Clearing unconditionally would wipe the highlight the fresh pass
        // is about to set, so a cancelled pass must leave it alone.
        guard !Task.isCancelled else { return }
        withAnimation { highlightedItemID = nil }
    }
}
