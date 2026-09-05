import SwiftUI
import WishlistKit

struct ClaimsView: View {
    let client: APIClient
    @State private var vm: ClaimsViewModel
    @State private var detailTarget: ItemDetail?

    init(client: APIClient) {
        self.client = client
        _vm = State(initialValue: ClaimsViewModel(client: client))
    }

    /// True while a query or the status filter narrows the list — drives the
    /// "No matches" empty state below.
    /// @spec IOS-GIFT-013
    private var isFiltering: Bool {
        !vm.query.isEmpty || vm.selectedStatus != nil
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.wlBg.ignoresSafeArea()
                VStack(spacing: 0) {
                    WLScreenTitle("My Claims")

                    // @spec IOS-GIFT-013 — status only; priority/category hidden.
                    FilterBar(status: $vm.selectedStatus,
                              priority: .constant(nil),
                              category: .constant(nil),
                              statusOptions: ["Claimed", "Purchased"],
                              categoryOptions: [],
                              showStatus: true,
                              showPriority: false,
                              showCategory: false)

                    // @spec IOS-GIFT-013 — the list is narrowed and nothing
                    // matches; distinct from the never-claimed state below.
                    if vm.filteredItems.isEmpty && !vm.isLoading && isFiltering {
                        Spacer()
                        ContentUnavailableView("No matches", systemImage: "magnifyingglass",
                                               description: Text("Nothing here matches your search or filters."))
                        Spacer()
                    } else if vm.items.isEmpty && !vm.isLoading {
                        Spacer()
                        ContentUnavailableView("No claims yet", systemImage: "gift",
                                               description: Text("Items you claim for others appear here."))
                        Spacer()
                    } else {
                        List {
                            if let error = vm.error {
                                Text(error).font(.footnote).foregroundStyle(Color.wlAccent)
                                    .listRowBackground(Color.clear).listRowSeparator(.hidden)
                            }
                            ForEach(vm.filteredItems) { item in
                                Button { Task { await openDetail(item) } } label: {
                                    ItemRow(item: item)
                                        .wlCard()
                                }
                                .buttonStyle(WLCardButtonStyle())
                                .listRowInsets(.init(top: 6, leading: 18, bottom: 6, trailing: 18))
                                .listRowSeparator(.hidden)
                                .listRowBackground(Color.clear)
                                .swipeActions(edge: .trailing) {
                                    if item.status == "Claimed" {
                                        Button("Unclaim", role: .destructive) { Task { await vm.unclaim(item) } }
                                        Button("Purchased") { Task { await vm.purchase(item) } }.tint(.wlGreen)
                                    }
                                }
                            }
                        }
                        .listStyle(.plain)
                        .scrollContentBackground(.hidden)
                        .refreshable { await vm.load() }
                        .searchable(text: $vm.query, prompt: "Search claims")
                    }
                }
            }
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .task { if vm.items.isEmpty { await vm.load() } }
        }
        .tint(.wlAccent)
        .fullScreenCover(item: $detailTarget) { target in
            DeepLinkDetailView(client: client, detail: target)
        }
    }

    /// Resolves the item's owner from the roster, then presents the item detail
    /// (same cover as a tapped push notification).
    /// @spec IOS-GIFT-009
    private func openDetail(_ item: Item) async {
        do {
            let owner = try await client.users().first { $0.id == item.userID }
            guard let owner else { return }
            detailTarget = ItemDetail(item: item, owner: owner)
        } catch {
            // Roster unavailable — stay on the list; nothing to show.
        }
    }
}
