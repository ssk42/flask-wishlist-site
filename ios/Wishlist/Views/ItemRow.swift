import AppIntents
import SwiftUI
import WishlistKit

struct ItemRow: View {
    let item: Item

    var body: some View {
        HStack(spacing: 13) {
            PriorityDot(priority: item.priority)
            VStack(alignment: .leading, spacing: 3) {
                Text(item.description)
                    .font(.body.weight(.medium))
                    .foregroundStyle(Color.wlInk)
                    .lineLimit(2)
                HStack(spacing: 8) {
                    if let price = item.price {
                        Text(price, format: .currency(code: "USD"))
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(Color.wlAccent)
                    }
                    if let category = item.category, !category.isEmpty {
                        Text(category)
                            .font(.caption)
                            .foregroundStyle(Color.wlSecondary)
                    }
                }
            }
            Spacer(minLength: 8)
            // @spec IOS-GIFT-008
            // Claim badge only for others' items (own items have nil status).
            if let status = item.status, status != "Available" {
                StatusPill(status: status)
            }
        }
        .padding(.vertical, 2)
        .modifier(ItemEntityAnnotation(itemID: item.id))
    }
}

/// Marks each row's on-screen entity so Siri knows which items are visible
/// while the user is browsing a list — the list-view counterpart to
/// `ItemEntityActivity` in `ItemDetailView.swift`, which handles the single-
/// entity detail screen. Apple's on-screen-content guidance calls for both.
///
/// iOS 18.4+ — a plain no-op below that, which keeps the deployment target at
/// 17.0. `appEntityIdentifier` is a SwiftUI view modifier vended by the
/// `_AppIntents_SwiftUI` cross-import overlay (loaded automatically when both
/// `SwiftUI` and `AppIntents` are imported).
private struct ItemEntityAnnotation: ViewModifier {
    let itemID: Int

    func body(content: Content) -> some View {
        if #available(iOS 18.4, *) {
            content.appEntityIdentifier(
                EntityIdentifier(for: ItemEntity.self, identifier: itemID)
            )
        } else {
            content
        }
    }
}
