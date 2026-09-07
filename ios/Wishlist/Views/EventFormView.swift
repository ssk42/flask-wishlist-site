import SwiftUI
import WishlistKit

/// Create/edit form for family events. Calls `onSave` with the trimmed name
/// and picked day; a `false` result keeps the form open so the surfaced
/// server message is not lost. Dismisses on success.
/// @spec IOS-EVT-006, IOS-EVT-007
struct EventFormView: View {
    let title: String
    var event: WishlistEvent?
    let onSave: (String, Date) async -> Bool

    @Environment(\.dismiss) private var dismiss
    @State private var name: String
    @State private var date: Date
    @State private var saving = false
    @State private var error: String?

    init(title: String, event: WishlistEvent? = nil,
         onSave: @escaping (String, Date) async -> Bool) {
        self.title = title
        self.event = event
        self.onSave = onSave
        _name = State(initialValue: event?.name ?? "")
        _date = State(initialValue: event?.date ?? Date())
    }

    private var trimmedName: String {
        name.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Name", text: $name)
                    DatePicker("Date", selection: $date, displayedComponents: .date)
                }
                if let error {
                    Section {
                        Text(error).font(.footnote).foregroundStyle(Color.wlAccent)
                    }
                }
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    // @spec IOS-EVT-006
                    Button("Save") { save() }.disabled(trimmedName.isEmpty || saving)
                }
            }
        }
    }

    private func save() {
        // @spec IOS-EVT-006, IOS-EVT-010
        saving = true
        error = nil
        let finalName = trimmedName
        let finalDate = date
        Task {
            let ok = await onSave(finalName, finalDate)
            saving = false
            if ok {
                dismiss()
            } else {
                error = "Couldn't save this event. Check the name and date."
            }
        }
    }
}
