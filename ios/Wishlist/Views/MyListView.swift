import SwiftUI
import WishlistKit

struct MyListView: View {
    let session: Session
    @State private var vm: MyListViewModel
    @State private var showingAdd = false
    @State private var editingItem: Item?
    @State private var confirmingLogout = false
    /// Events list feeding the item form's event picker (owner-only link).
    /// @spec IOS-EVT-012
    @State private var events: [WishlistEvent] = []

    init(session: Session) {
        self.session = session
        // @spec IOS-CUR-010 — nil while logged out; the body renders a log-in
        // prompt and never loads, so userID 0 is never queried.
        let userID = MyListViewModel.userID(from: session.state) ?? 0
        _vm = State(initialValue: MyListViewModel(client: session.client, userID: userID))
    }

    /// Distinct sorted categories present in the loaded items — the category
    /// filter's options.
    /// @spec IOS-CUR-011
    private var categoryOptions: [String] {
        Array(Set(vm.items.compactMap(\.category).filter { !$0.isEmpty })).sorted()
    }

    /// True while a query or any filter narrows the list — drives the
    /// "No matches" state below.
    /// @spec IOS-CUR-011
    private var isFiltering: Bool {
        !vm.query.isEmpty || vm.selectedPriority != nil || vm.selectedCategory != nil
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
                    if MyListViewModel.userID(from: session.state) == nil {
                        // @spec IOS-CUR-010
                        Spacer()
                        ContentUnavailableView("Log in to see your list", systemImage: "person.crop.circle",
                                                   description: Text("Your saved items are waiting."))
                    } else if vm.filteredItems.isEmpty && isFiltering {
                        // @spec IOS-CUR-009, IOS-CUR-011
                        Spacer()
                        ContentUnavailableView("No matches", systemImage: "magnifyingglass",
                                                   description: Text("Nothing on your list matches your search."))
                        Spacer()
                    } else if vm.items.isEmpty && !vm.isLoading {
                        Spacer()
                        ContentUnavailableView("Your list is empty", systemImage: "sparkles",
                                                   description: Text("Tap + to add something you're wishing for."))
                        Spacer()
                    } else {
                        VStack(spacing: 0) {
                            // @spec IOS-CUR-011 — priority/category only; own
                            // items have nil status, so no status filter.
                            FilterBar(status: .constant(nil),
                                      priority: $vm.selectedPriority,
                                      category: $vm.selectedCategory,
                                      statusOptions: [],
                                      categoryOptions: categoryOptions,
                                      showStatus: false)
                            List {
                                if let error = vm.error {
                                    Text(error).font(.footnote).foregroundStyle(Color.wlAccent)
                                        .listRowBackground(Color.clear).listRowSeparator(.hidden)
                                }
                                // @spec IOS-CUR-007 — own items have nil status, so rows render no claim badge/actions.
                                // @spec IOS-CUR-009 — render the filtered list; deletion
                                // resolves by id so the intended item goes while filtered.
                                ForEach(vm.filteredItems) { item in
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
                                    let toDelete = indexSet.map { vm.filteredItems[$0] }
                                    Task { for item in toDelete { await vm.delete(item) } }
                                }
                            }
                            .listStyle(.plain)
                            .scrollContentBackground(.hidden)
                            .refreshable { await vm.load() }
                        }
                        .searchable(text: $vm.query, prompt: "Search your list")
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
            .task { if vm.items.isEmpty && MyListViewModel.userID(from: session.state) != nil { await vm.load() } }
            .task { await loadEvents() }
            .sheet(isPresented: $showingAdd) {
                ItemEditView(title: "Add Item",
                             onSave: { draft in await vm.create(draft) },
                             onPrefill: { url in await vm.prefill(url: url) },
                             events: events)
            }
            .sheet(item: $editingItem) { item in
                ItemEditView(title: "Edit Item", item: item,
                             onSave: { draft in await vm.update(id: item.id, draft) },
                             onPrefill: { url in await vm.prefill(url: url) },
                             events: events)
            }
        }
        .tint(.wlAccent)
    }

    /// Best-effort events fetch for the picker; a failure just leaves the
    /// picker hidden (the form renders it only when the list is non-empty).
    /// @spec IOS-EVT-012
    private func loadEvents() async {
        guard MyListViewModel.userID(from: session.state) != nil else { return }
        if let fetched = try? await session.client.events() {
            events = fetched
        }
    }
}
