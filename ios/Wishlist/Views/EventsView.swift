import SwiftUI
import WishlistKit

/// Events tab: upcoming + past family events, with creator-side create/edit/delete.
/// @spec IOS-EVT-001, IOS-EVT-006
struct EventsView: View {
    let session: Session
    var client: APIClient { session.client }
    /// Nil while logged out; edit/delete affordances stay hidden then.
    /// @spec IOS-EVT-009
    var currentUserID: Int? { MyListViewModel.userID(from: session.state) }
    @State private var vm: EventsViewModel
    @State private var showingAdd = false

    init(session: Session) {
        self.session = session
        _vm = State(initialValue: EventsViewModel(client: session.client))
    }

    /// Upcoming first, date ascending.
    /// @spec IOS-EVT-003
    private var upcomingSorted: [WishlistEvent] {
        vm.upcoming.sorted { $0.date < $1.date }
    }

    private var isEmpty: Bool {
        vm.upcoming.isEmpty && vm.past.isEmpty
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.wlBg.ignoresSafeArea()
                VStack(spacing: 0) {
                    WLScreenTitle("Events")

                    // @spec IOS-EVT-005
                    if isEmpty && !vm.isLoading {
                        Spacer()
                        ContentUnavailableView("No events yet", systemImage: "calendar",
                                               description: Text("Family events will show up here."))
                        Spacer()
                    } else {
                        List {
                            // @spec IOS-EVT-004
                            if let error = vm.error {
                                HStack {
                                    Text(error).font(.footnote).foregroundStyle(Color.wlAccent)
                                    Spacer()
                                    Button("Retry") { Task { await vm.load() } }
                                        .font(.footnote.weight(.semibold))
                                        .foregroundStyle(Color.wlAccent)
                                }
                                .listRowBackground(Color.clear).listRowSeparator(.hidden)
                            }
                            if !upcomingSorted.isEmpty {
                                Section("Upcoming") {
                                    ForEach(upcomingSorted) { event in
                                        NavigationLink {
                                            EventDetailView(client: client, event: event, vm: vm, currentUserID: currentUserID)
                                        } label: {
                                            EventCard(event: event)
                                        }
                                        .listRowInsets(.init(top: 6, leading: 18, bottom: 6, trailing: 18))
                                        .listRowSeparator(.hidden)
                                        .listRowBackground(Color.clear)
                                    }
                                }
                            }
                            if !vm.past.isEmpty {
                                Section("Past") {
                                    ForEach(vm.past) { event in
                                        NavigationLink {
                                            EventDetailView(client: client, event: event, vm: vm, currentUserID: currentUserID)
                                        } label: {
                                            EventCard(event: event)
                                                .opacity(0.7)
                                        }
                                        .listRowInsets(.init(top: 6, leading: 18, bottom: 6, trailing: 18))
                                        .listRowSeparator(.hidden)
                                        .listRowBackground(Color.clear)
                                    }
                                }
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
                // @spec IOS-EVT-006
                ToolbarItem(placement: .primaryAction) {
                    Button { showingAdd = true } label: {
                        Label("Add Event", systemImage: "plus")
                    }
                }
            }
            .task { if isEmpty { await vm.load() } }
            .sheet(isPresented: $showingAdd) {
                EventFormView(title: "Add Event") { name, date in
                    await vm.create(name: name, date: date)
                }
            }
        }
        .tint(.wlAccent)
    }
}

/// One event row: date badge + name + creator + item-count badge,
/// mirroring the web event card (badge hidden when the count is 0).
struct EventCard: View {
    let event: WishlistEvent

    var body: some View {
        HStack(spacing: 12) {
            EventDateBadge(date: event.date)
            VStack(alignment: .leading, spacing: 4) {
                Text(event.name)
                    .font(.headline)
                    .foregroundStyle(Color.wlInk)
                    .multilineTextAlignment(.leading)
                Text("Created by \(event.createdBy.name)")
                    .font(.footnote)
                    .foregroundStyle(Color.wlSecondary)
                if event.itemCount > 0 {
                    Text("\(event.itemCount) items")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(Color.wlSecondary)
                        .padding(.horizontal, 8).padding(.vertical, 3)
                        .background(Color.wlAccentSoft)
                        .clipShape(Capsule())
                }
            }
            Spacer()
        }
        .wlCard(padding: 14)
    }
}

/// Month-over-day badge, mirroring the web card's date badge.
struct EventDateBadge: View {
    let date: Date
    var large = false

    var body: some View {
        VStack(spacing: 0) {
            Text(EventDateBadge.monthFormatter.string(from: date).uppercased())
                .font(large ? .subheadline.weight(.bold) : .caption.weight(.bold))
                .foregroundStyle(Color.wlAccent)
            Text(EventDateBadge.dayFormatter.string(from: date))
                .font(large ? .wlDisplay(32) : .wlDisplay(24))
                .foregroundStyle(Color.wlInk)
        }
        .frame(width: large ? 72 : 56, height: large ? 72 : 60)
        .background(Color.wlAccentSoft)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private static let monthFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "MMM"
        return f
    }()

    private static let dayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "d"
        return f
    }()
}
