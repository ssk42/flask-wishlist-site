import SwiftUI
import WishlistKit

struct MemberItemsView: View {
    let client: APIClient
    @State private var vm: MemberItemsViewModel

    init(client: APIClient, member: User) {
        self.client = client
        _vm = State(initialValue: MemberItemsViewModel(client: client, member: member))
    }

    var body: some View {
        List {
            if let error = vm.error {
                Text(error).foregroundStyle(.red).font(.footnote)
            }
            ForEach(vm.items) { item in
                NavigationLink(value: item) { ItemRow(item: item) }
            }
        }
        .overlay {
            if vm.items.isEmpty && !vm.isLoading {
                ContentUnavailableView("No items yet", systemImage: "gift")
            }
        }
        .navigationTitle(vm.member.name)
        .navigationDestination(for: Item.self) { item in
            ItemDetailView(item: item, vm: vm)
        }
        .refreshable { await vm.load() }
        .task { if vm.items.isEmpty { await vm.load() } }
    }
}
