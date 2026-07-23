import SwiftUI
import WishlistKit

struct ClaimsView: View {
    let client: APIClient
    @State private var vm: ClaimsViewModel

    init(client: APIClient) {
        self.client = client
        _vm = State(initialValue: ClaimsViewModel(client: client))
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.wlBg.ignoresSafeArea()
                if vm.items.isEmpty && !vm.isLoading {
                    ContentUnavailableView("No claims yet", systemImage: "gift",
                                           description: Text("Items you claim for others appear here."))
                } else {
                    List {
                        if let error = vm.error {
                            Text(error).font(.footnote).foregroundStyle(Color.wlAccent)
                                .listRowBackground(Color.clear).listRowSeparator(.hidden)
                        }
                        ForEach(vm.items) { item in
                            ItemRow(item: item)
                                .wlCard()
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
                }
            }
            .navigationTitle("My Claims")
            .task { if vm.items.isEmpty { await vm.load() } }
        }
        .tint(.wlAccent)
    }
}
