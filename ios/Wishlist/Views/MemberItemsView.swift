import SwiftUI
import WishlistKit

struct MemberItemsView: View {
    let client: APIClient
    @State private var vm: MemberItemsViewModel
    /// The item Siri (or a deep link) asked to open, if any. Cleared once
    /// it's been scrolled to and briefly highlighted — this is a one-shot
    /// focus affordance, not persistent state.
    @State private var highlightedItemID: Int?

    init(client: APIClient, member: User, highlightItemID: Int? = nil) {
        self.client = client
        _vm = State(initialValue: MemberItemsViewModel(client: client, member: member))
        _highlightedItemID = State(initialValue: highlightItemID)
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
        guard let id = highlightedItemID, vm.items.contains(where: { $0.id == id }) else { return }
        withAnimation { proxy.scrollTo(id, anchor: .center) }
        try? await Task.sleep(for: .seconds(1.5))
        withAnimation { highlightedItemID = nil }
    }
}
