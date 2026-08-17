import SwiftUI
import WishlistKit

/// A full-screen host for a deep-linked item, dedicated to what a tapped push
/// notification routed to. It loads the owner's items through the same
/// `MemberItemsViewModel` used by the normal Family → member → item flow, so
/// `ItemDetailView`'s live `current` resolution and claim/purchase mutation work
/// unchanged. Close is the only exit (dismiss via the cover's swipe-down).
struct DeepLinkDetailView: View {
    let client: APIClient
    let detail: ItemDetail
    @Environment(\.dismiss) private var dismiss
    @State private var vm: MemberItemsViewModel

    init(client: APIClient, detail: ItemDetail) {
        self.client = client
        self.detail = detail
        _vm = State(initialValue: MemberItemsViewModel(client: client, member: detail.owner))
    }

    var body: some View {
        NavigationStack {
            ItemDetailView(item: detail.item, vm: vm)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Done") { dismiss() }
                    }
                }
        }
        .task { if vm.items.isEmpty { await vm.load() } }
    }
}