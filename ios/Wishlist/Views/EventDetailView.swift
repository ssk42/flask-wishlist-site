import SwiftUI
import WishlistKit

/// A single event: name, full date, creator, and its items, read-only.
/// @spec IOS-EVT-002
struct EventDetailView: View {
    let client: APIClient
    let event: WishlistEvent
    @State private var items: [Item] = []
    @State private var isLoading = false
    @State private var error: String?
    @State private var detailTarget: ItemDetail?

    var body: some View {
        ZStack {
            Color.wlBg.ignoresSafeArea()
            VStack(spacing: 0) {
                header
                    .padding(.horizontal, 18).padding(.top, 8)

                if let error {
                    HStack {
                        Text(error).font(.footnote).foregroundStyle(Color.wlAccent)
                        Spacer()
                        Button("Retry") { Task { await load() } }
                            .font(.footnote.weight(.semibold))
                            .foregroundStyle(Color.wlAccent)
                    }
                    .padding(.horizontal, 18).padding(.top, 8)
                }

                if items.isEmpty && !isLoading {
                    Spacer()
                    ContentUnavailableView("No items yet", systemImage: "gift",
                                           description: Text("Items linked to this event will show up here."))
                    Spacer()
                } else {
                    List {
                        ForEach(items) { item in
                            Button { Task { await openDetail(item) } } label: {
                                ItemRow(item: item)
                                    .wlCard()
                            }
                            .buttonStyle(WLCardButtonStyle())
                            .listRowInsets(.init(top: 6, leading: 18, bottom: 6, trailing: 18))
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                        }
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                    .refreshable { await load() }
                }
            }
        }
        .navigationTitle(event.name)
        .navigationBarTitleDisplayMode(.inline)
        .task { if items.isEmpty { await load() } }
        .fullScreenCover(item: $detailTarget) { target in
            DeepLinkDetailView(client: client, detail: target)
        }
    }

    private var header: some View {
        HStack(spacing: 14) {
            EventDateBadge(date: event.date, large: true)
            VStack(alignment: .leading, spacing: 4) {
                Text(event.name)
                    .font(.wlTitle)
                    .foregroundStyle(Color.wlInk)
                Text(event.date.formatted(date: .complete, time: .omitted))
                    .font(.subheadline)
                    .foregroundStyle(Color.wlSecondary)
                Text("Created by \(event.createdBy.name)")
                    .font(.subheadline)
                    .foregroundStyle(Color.wlSecondary)
            }
            Spacer()
        }
    }

    /// Loads items via `client.event(id:)` (masked, surprise-safe).
    /// @spec IOS-EVT-002
    private func load() async {
        isLoading = true
        error = nil
        do {
            items = try await client.event(id: event.id).items
        } catch {
            self.error = "Couldn't load items."
        }
        isLoading = false
    }

    /// Resolves the item's owner from the roster, then presents the item detail
    /// (same cover as a tapped push notification).
    /// @spec IOS-GIFT-009
    private func openDetail(_ item: Item) async {
        do {
            let owner = try await client.users().first { $0.id == item.userID }
            guard let owner else { return }
            detailTarget = ItemDetail(item: item, owner: owner)
        } catch {
            // Roster unavailable — stay on the list; nothing to show.
        }
    }
}
