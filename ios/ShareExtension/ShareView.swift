import SwiftUI
import WishlistKit

/// The sheet shown when sharing a product URL into Wishlist.
struct ShareView: View {
    let vm: ShareItemViewModel
    let urlString: String
    let onFinished: () -> Void
    let onCancel: () -> Void

    @State private var priceText = ""
    @State private var saving = false

    private let priorities = ["High", "Medium", "Low"]
    @State private var priority = "Medium"

    var body: some View {
        NavigationStack {
            ZStack {
                Color.wlShareBg.ignoresSafeArea()
                Form {
                    Section {
                        TextField("What is it?", text: Binding(
                            get: { vm.draft.description ?? "" },
                            set: { vm.draft.description = $0 }
                        ), axis: .vertical)
                        TextField("Price", text: $priceText)
                            .keyboardType(.decimalPad)
                        Picker("Priority", selection: $priority) {
                            ForEach(priorities, id: \.self) { Text($0) }
                        }
                    } header: {
                        Text("Add to your wishlist")
                    } footer: {
                        Text(urlString).lineLimit(2).font(.caption2)
                    }

                    if vm.isLoading {
                        HStack(spacing: 8) {
                            ProgressView()
                            Text("Looking up details…").foregroundStyle(.secondary)
                        }
                    }
                    if let error = vm.error {
                        Text(error).font(.footnote).foregroundStyle(.red)
                    }
                }
                .scrollContentBackground(.hidden)
            }
            .navigationTitle("Wishlist")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", action: onCancel)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save() }
                        .disabled(!vm.canSubmit || saving || vm.needsLogin)
                }
            }
        }
        .task {
            await vm.prefill(urlString: urlString)
            if let price = vm.draft.price { priceText = String(price) }
        }
    }

    private func save() {
        saving = true
        vm.draft.price = Double(priceText)
        vm.draft.priority = priority
        Task {
            let ok = await vm.submit()
            saving = false
            if ok { onFinished() }
        }
    }
}

private extension Color {
    /// The extension can't see the app target's Theme.swift, so it carries the
    /// one colour it needs (same cream as Theme.wlBg).
    static let wlShareBg = Color(uiColor: UIColor { trait in
        trait.userInterfaceStyle == .dark
            ? UIColor(red: 0x16/255, green: 0x12/255, blue: 0x0E/255, alpha: 1)
            : UIColor(red: 0xFB/255, green: 0xF6/255, blue: 0xEF/255, alpha: 1)
    })
}
