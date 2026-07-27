import AppIntents
import SwiftUI
import WishlistKit

struct ItemDetailView: View {
    let item: Item
    let vm: MemberItemsViewModel
    @State private var working = false

    private var current: Item { vm.items.first(where: { $0.id == item.id }) ?? item }

    var body: some View {
        ZStack {
            Color.wlBg.ignoresSafeArea()
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    // Header card
                    VStack(alignment: .leading, spacing: 10) {
                        Text(current.description)
                            .font(.wlTitle)
                            .foregroundStyle(Color.wlInk)
                        if let price = current.price {
                            Text(price, format: .currency(code: "USD"))
                                .font(.title3.weight(.bold))
                                .foregroundStyle(Color.wlAccent)
                        }
                        HStack(spacing: 14) {
                            if let priority = current.priority {
                                Label(priority, systemImage: "flag.fill")
                                    .font(.caption).foregroundStyle(Color.wlSecondary)
                            }
                            if let category = current.category, !category.isEmpty {
                                Label(category, systemImage: "tag.fill")
                                    .font(.caption).foregroundStyle(Color.wlSecondary)
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .wlCard(padding: 20)

                    // Variants
                    if hasVariants {
                        VStack(spacing: 0) {
                            variantRow("Size", current.size)
                            variantRow("Color", current.color)
                            variantRow("Quantity", current.quantity.map(String.init))
                        }
                        .wlCard(padding: 4)
                    }

                    if let link = current.link, let url = URL(string: link) {
                        Link(destination: url) {
                            Label("View product", systemImage: "safari")
                                .font(.subheadline.weight(.medium))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                                .foregroundStyle(Color.wlAccent)
                                .background(Color.wlAccentSoft, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                        }
                    }

                    // Gift actions — only for others' items (status non-nil)
                    if let status = current.status {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Text("Gift status").font(.headline).foregroundStyle(Color.wlInk)
                                Spacer()
                                StatusPill(status: status)
                            }
                            actionButtons(status: status)
                            if let error = vm.error {
                                Text(error).font(.footnote).foregroundStyle(Color.wlAccent)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .wlCard(padding: 20)
                    }
                }
                .padding(.horizontal, 18).padding(.top, 8)
            }
        }
        .modifier(ItemEntityActivity(itemID: current.id, title: current.description))
        .navigationTitle("Item")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var hasVariants: Bool {
        current.size != nil || current.color != nil || current.quantity != nil
    }

    @ViewBuilder
    private func variantRow(_ label: String, _ value: String?) -> some View {
        if let value, !value.isEmpty {
            HStack {
                Text(label).foregroundStyle(Color.wlSecondary)
                Spacer()
                Text(value).foregroundStyle(Color.wlInk).fontWeight(.medium)
            }
            .font(.subheadline)
            .padding(.horizontal, 16).padding(.vertical, 12)
        }
    }

    @ViewBuilder
    private func actionButtons(status: String) -> some View {
        VStack(spacing: 10) {
            if status == "Available" {
                primary("Claim it", "hand.raised.fill") { await vm.claim(current) }
                secondary("Mark purchased", "checkmark.circle") { await vm.purchase(current) }
            } else if status == "Claimed" {
                secondary("Unclaim", "arrow.uturn.backward") { await vm.unclaim(current) }
                primary("Mark purchased", "checkmark.circle.fill") { await vm.purchase(current) }
            }
        }
        .disabled(working)
    }

    private func primary(_ title: String, _ icon: String, _ work: @escaping () async -> Void) -> some View {
        Button { act(work) } label: {
            Label(title, systemImage: icon).font(.headline)
                .frame(maxWidth: .infinity).padding(.vertical, 14)
                .background(Color.wlAccent, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                .foregroundStyle(.white)
        }
    }

    private func secondary(_ title: String, _ icon: String, _ work: @escaping () async -> Void) -> some View {
        Button { act(work) } label: {
            Label(title, systemImage: icon).font(.subheadline.weight(.medium))
                .frame(maxWidth: .infinity).padding(.vertical, 13)
                .foregroundStyle(Color.wlInk)
                .background(Color.wlHairline.opacity(0.5), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        }
    }

    private func act(_ work: @escaping () async -> Void) {
        working = true
        Task { await work(); working = false }
    }
}

/// Publishes the item on screen as the current `NSUserActivity`, tagged with its
/// `ItemEntity` identifier, so Siri can resolve "claim this" to the item the
/// user is actually looking at.
///
/// iOS 18.2+ — a plain no-op below that, which keeps the deployment target at
/// 17.0. There is no SwiftUI `appEntityIdentifier` view modifier; the property
/// lives on `NSUserActivity` via `AppEntityAnnotatable`.
private struct ItemEntityActivity: ViewModifier {
    let itemID: Int
    let title: String

    func body(content: Content) -> some View {
        if #available(iOS 18.2, *) {
            content.userActivity("com.reitz.wishlist.viewItem") { activity in
                activity.appEntityIdentifier = EntityIdentifier(
                    for: ItemEntity.self, identifier: itemID
                )
                activity.title = title
                // Deliberately NOT eligibleForSearch/eligibleForPublicIndexing:
                // an item's name is other people's gift information and must not
                // be indexed outside the app. See the surprise-protection note.
                activity.isEligibleForHandoff = false
            }
        } else {
            content
        }
    }
}
