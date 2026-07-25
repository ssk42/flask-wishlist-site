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
        ZStack {
            Color.wlBg.ignoresSafeArea()
            if vm.items.isEmpty && !vm.isLoading {
                ContentUnavailableView("No items yet", systemImage: "gift")
            } else {
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
                            }
                            .buttonStyle(WLCardButtonStyle())
                        }
                    }
                    .padding(.horizontal, 18).padding(.top, 8)
                }
                .refreshable { await vm.load() }
            }
        }
        .navigationTitle(vm.member.name)
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: Item.self) { item in
            ItemDetailView(item: item, vm: vm)
        }
        .task { if vm.items.isEmpty { await vm.load() } }
    }
}
