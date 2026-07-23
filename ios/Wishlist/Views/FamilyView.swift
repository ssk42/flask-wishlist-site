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
            Group {
                if vm.isLoading && vm.users.isEmpty {
                    ProgressView()
                } else if let error = vm.error, vm.users.isEmpty {
                    ContentUnavailableView("Couldn't load", systemImage: "wifi.slash", description: Text(error))
                } else {
                    List(vm.users) { user in
                        NavigationLink(value: user) {
                            HStack {
                                Text(user.name)
                                Spacer()
                                if let count = user.itemCount {
                                    Text("\(count)").foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                    .refreshable { await vm.load() }
                }
            }
            .navigationTitle("Family")
            .navigationDestination(for: User.self) { user in
                MemberItemsView(client: client, member: user)
            }
        }
        .task { if vm.users.isEmpty { await vm.load() } }
    }
}
