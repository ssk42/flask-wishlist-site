import SwiftUI
import WishlistKit

/// Add/edit form for the current user's own items. Calls `onSave` with a draft;
/// returns true to dismiss.
struct ItemEditView: View {
    let title: String
    var item: Item?
    let onSave: (ItemDraft) async -> Bool

    @Environment(\.dismiss) private var dismiss
    @State private var description: String
    @State private var link: String
    @State private var priceText: String
    @State private var category: String
    @State private var priority: String
    @State private var size: String
    @State private var color: String
    @State private var quantityText: String
    @State private var saving = false

    private let priorities = ["High", "Medium", "Low"]

    init(title: String, item: Item? = nil, onSave: @escaping (ItemDraft) async -> Bool) {
        self.title = title
        self.item = item
        self.onSave = onSave
        _description = State(initialValue: item?.description ?? "")
        _link = State(initialValue: item?.link ?? "")
        _priceText = State(initialValue: item?.price.map { String($0) } ?? "")
        _category = State(initialValue: item?.category ?? "")
        _priority = State(initialValue: item?.priority ?? "Medium")
        _size = State(initialValue: item?.size ?? "")
        _color = State(initialValue: item?.color ?? "")
        _quantityText = State(initialValue: item?.quantity.map(String.init) ?? "")
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Description", text: $description, axis: .vertical)
                    TextField("Link (https://…)", text: $link)
                        .keyboardType(.URL).autocorrectionDisabled().textInputAutocapitalization(.never)
                    TextField("Price", text: $priceText).keyboardType(.decimalPad)
                    TextField("Category", text: $category)
                    Picker("Priority", selection: $priority) {
                        ForEach(priorities, id: \.self) { Text($0) }
                    }
                }
                Section("Options") {
                    TextField("Size", text: $size)
                    TextField("Color", text: $color)
                    TextField("Quantity", text: $quantityText).keyboardType(.numberPad)
                }
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save() }.disabled(description.isEmpty || saving)
                }
            }
        }
    }

    private func save() {
        saving = true
        let draft = ItemDraft(
            description: description,
            link: link.isEmpty ? nil : link,
            price: Double(priceText),
            category: category.isEmpty ? nil : category,
            priority: priority,
            size: size.isEmpty ? nil : size,
            color: color.isEmpty ? nil : color,
            quantity: Int(quantityText)
        )
        Task {
            let ok = await onSave(draft)
            saving = false
            if ok { dismiss() }
        }
    }
}
