import SwiftUI
import WishlistKit

struct MyListView: View {
    let session: Session
    @State private var vm: MyListViewModel
    @State private var showingAdd = false
    @State private var editingItem: Item?
    @State private var confirmingLogout = false

    init(session: Session) {
        self.session = session
        let userID: Int = { if case .loggedIn(let u) = session.state { return u.id }; return 0 }()
        _vm = State(initialValue: MyListViewModel(client: session.client, userID: userID))
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.wlBg.ignoresSafeArea()
                VStack(spacing: 0) {
                    WLScreenTitle("My List") {
                        Button { showingAdd = true } label: {
                            Image(systemName: "plus.circle.fill")
                                .font(.title2)
                                .foregroundStyle(Color.wlAccent)
                        }
                    }

                    if vm.items.isEmpty && !vm.isLoading {
                        Spacer()
                        ContentUnavailableView("Your list is empty", systemImage: "sparkles",
                                               description: Text("Tap + to add something you're wishing for."))
                        Spacer()
                    } else {
                        List {
                            if let error = vm.error {
                                Text(error).font(.footnote).foregroundStyle(Color.wlAccent)
                                    .listRowBackground(Color.clear).listRowSeparator(.hidden)
                            }
                            // @spec IOS-CUR-007 — own items have nil status, so rows render no claim badge/actions.
                            ForEach(vm.items) { item in
                                Button { editingItem = item } label: {
                                    HStack {
                                        ItemRow(item: item)
                                        Image(systemName: "pencil")
                                            .font(.footnote).foregroundStyle(Color.wlSecondary.opacity(0.5))
                                    }
                                    .wlCard()
                                }
                                .buttonStyle(WLCardButtonStyle())
                                .listRowInsets(.init(top: 6, leading: 18, bottom: 6, trailing: 18))
                                .listRowSeparator(.hidden)
                                .listRowBackground(Color.clear)
                            }
                            .onDelete { indexSet in
                                let toDelete = indexSet.map { vm.items[$0] }
                                Task { for item in toDelete { await vm.delete(item) } }
                            }
                        }
                        .listStyle(.plain)
                        .scrollContentBackground(.hidden)
                        .refreshable { await vm.load() }
                    }
                }
            }
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button("Log out", role: .destructive) { confirmingLogout = true }
                    } label: {
                        Image(systemName: "gearshape")
                            .foregroundStyle(Color.wlSecondary)
                    }
                }
            }
            .confirmationDialog("Log out?", isPresented: $confirmingLogout, titleVisibility: .visible) {
                // @spec IOS-AUTH-008
                Button("Log out", role: .destructive) {
                    Task { await session.logOut() }
                }
            } message: {
                Text("Your saved items stay on your wishlist.")
            }
            .task { if vm.items.isEmpty { await vm.load() } }
            .sheet(isPresented: $showingAdd) {
                ItemEditView(title: "Add Item",
                             onSave: { draft in await vm.create(draft) },
                             onPrefill: { url in await vm.prefill(url: url) })
            }
            .sheet(item: $editingItem) { item in
                ItemEditView(title: "Edit Item", item: item,
                             onSave: { draft in await vm.update(id: item.id, draft) },
                             onPrefill: { url in await vm.prefill(url: url) })
            }
        }
        .tint(.wlAccent)
    }
}
