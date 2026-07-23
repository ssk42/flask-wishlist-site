import SwiftUI
import WishlistKit

struct ItemDetailView: View {
    let item: Item
    let vm: MemberItemsViewModel
    @State private var working = false

    /// Reads the live item from the view model so claim/purchase actions reflect
    /// immediately; falls back to the passed item.
    private var current: Item { vm.items.first(where: { $0.id == item.id }) ?? item }

    var body: some View {
        Form {
            Section {
                Text(current.description)
                if let price = current.price {
                    LabeledContent("Price", value: price, format: .currency(code: "USD"))
                }
                if let category = current.category { LabeledContent("Category", value: category) }
                if let priority = current.priority { LabeledContent("Priority", value: priority) }
                if let size = current.size { LabeledContent("Size", value: size) }
                if let color = current.color { LabeledContent("Color", value: color) }
                if let quantity = current.quantity { LabeledContent("Quantity", value: "\(quantity)") }
                if let link = current.link, let url = URL(string: link) {
                    Link("View product", destination: url)
                }
            }

            if let status = current.status {
                Section("Gift status") {
                    LabeledContent("Status", value: status)
                    if status == "Available" {
                        Button("Claim") { act { await vm.claim(current) } }
                        Button("Mark purchased") { act { await vm.purchase(current) } }
                    } else if status == "Claimed" {
                        Button("Unclaim", role: .destructive) { act { await vm.unclaim(current) } }
                        Button("Mark purchased") { act { await vm.purchase(current) } }
                    }
                }
                .disabled(working)
            }

            if let error = vm.error {
                Text(error).foregroundStyle(.red).font(.footnote)
            }
        }
        .navigationTitle("Item")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func act(_ work: @escaping () async -> Void) {
        working = true
        Task { await work(); working = false }
    }
}
