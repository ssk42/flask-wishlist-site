import SwiftUI
import WishlistKit

struct ItemRow: View {
    let item: Item

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(item.description).lineLimit(2)
                if let price = item.price {
                    Text(price, format: .currency(code: "USD"))
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            Spacer()
            // Claim badge shows ONLY for other people's items (status non-nil).
            // Own items have nil status (server hides it) and never show a badge.
            if let status = item.status, status != "Available" {
                Text(status)
                    .font(.caption2)
                    .padding(.horizontal, 6).padding(.vertical, 2)
                    .background(status == "Purchased" ? Color.green.opacity(0.2) : Color.orange.opacity(0.2))
                    .clipShape(Capsule())
            }
        }
    }
}
