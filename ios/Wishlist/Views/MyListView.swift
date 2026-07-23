import SwiftUI
import WishlistKit

struct MyListView: View {
    let session: Session
    @State private var vm: MyListViewModel
    @State private var showingAdd = false
    @State private var editingItem: Item?

    init(session: Session) {
        self.session = session
        let userID: Int = { if case .loggedIn(let u) = session.state { return u.id }; return 0 }()
        _vm = State(initialValue: MyListViewModel(client: session.client, userID: userID))
    }

    var body: some View {
        NavigationStack {
            List {
                if let error = vm.error {
                    Text(error).foregroundStyle(.red).font(.footnote)
                }
                ForEach(vm.items) { item in
                    Button { editingItem = item } label: {
                        ItemRow(item: item).foregroundStyle(.primary)
                    }
                }
                .onDelete { indexSet in
                    let toDelete = indexSet.map { vm.items[$0] }
                    Task { for item in toDelete { await vm.delete(item) } }
                }
            }
            .overlay {
                if vm.items.isEmpty && !vm.isLoading {
                    ContentUnavailableView("Your list is empty", systemImage: "list.bullet",
                                           description: Text("Tap + to add something you want."))
                }
            }
            .navigationTitle("My List")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button { showingAdd = true } label: { Image(systemName: "plus") }
                }
            }
            .refreshable { await vm.load() }
            .task { if vm.items.isEmpty { await vm.load() } }
            .sheet(isPresented: $showingAdd) {
                ItemEditView(title: "Add Item") { draft in await vm.create(draft) }
            }
            .sheet(item: $editingItem) { item in
                ItemEditView(title: "Edit Item", item: item) { draft in await vm.update(id: item.id, draft) }
            }
        }
    }
}
