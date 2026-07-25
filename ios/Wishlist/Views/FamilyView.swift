import SwiftUI
import WishlistKit

struct FamilyView: View {
    let client: APIClient
    @State private var vm: FamilyViewModel

    init(client: APIClient) {
        self.client = client
        _vm = State(initialValue: FamilyViewModel(client: client))
    }

    var body: some View {
        NavigationStack {
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
        }
        .tint(.wlAccent)
        .task { if vm.users.isEmpty { await vm.load() } }
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
