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
            // Claim badge only for others' items (own items have nil status).
            if let status = item.status, status != "Available" {
                StatusPill(status: status)
            }
        }
        .padding(.vertical, 2)
    }
}
