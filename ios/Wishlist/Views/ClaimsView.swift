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
            List {
                if let error = vm.error {
                    Text(error).foregroundStyle(.red).font(.footnote)
                }
                ForEach(vm.items) { item in
                    ItemRow(item: item)
                        .swipeActions(edge: .trailing) {
                            if item.status == "Claimed" {
                                Button("Unclaim", role: .destructive) { Task { await vm.unclaim(item) } }
                                Button("Purchased") { Task { await vm.purchase(item) } }.tint(.green)
                            }
                        }
                }
            }
            .overlay {
                if vm.items.isEmpty && !vm.isLoading {
                    ContentUnavailableView("No claims yet", systemImage: "gift",
                                           description: Text("Items you claim for others appear here."))
                }
            }
            .navigationTitle("My Claims")
            .refreshable { await vm.load() }
            .task { if vm.items.isEmpty { await vm.load() } }
        }
    }
}
