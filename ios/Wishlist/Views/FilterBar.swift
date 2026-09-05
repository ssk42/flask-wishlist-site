import SwiftUI

/// Compact horizontally-scrolling filter chip row.
///
/// Each chip is a `Menu` showing "All" + options, with a checkmark on the
/// current selection and an accent highlight while a value is set. `nil`
/// means All for every binding.
/// @spec IOS-GIFT-011, IOS-GIFT-012, IOS-GIFT-013, IOS-CUR-011
struct FilterBar: View {
    @Binding var status: String?
    @Binding var priority: String?
    @Binding var category: String?
    let statusOptions: [String]
    let categoryOptions: [String]
    var showStatus: Bool = true
    var showPriority: Bool = true
    var showCategory: Bool = true

    /// Fixed priority vocabulary — matches the server's High/Medium/Low.
    static let priorityOptions = ["High", "Medium", "Low"]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                if showStatus {
                    FilterChip(title: "Status", selection: $status, options: statusOptions)
                }
                if showPriority {
                    FilterChip(title: "Priority", selection: $priority, options: Self.priorityOptions)
                }
                if showCategory {
                    FilterChip(title: "Category", selection: $category, options: categoryOptions)
                }
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 8)
        }
    }
}

private struct FilterChip: View {
    let title: String
    @Binding var selection: String?
    let options: [String]

    var body: some View {
        Menu {
            Button("All") { selection = nil }
            ForEach(options, id: \.self) { option in
                Button {
                    selection = option
                } label: {
                    if selection == option {
                        Label(option, systemImage: "checkmark")
                    } else {
                        Text(option)
                    }
                }
            }
        } label: {
            HStack(spacing: 4) {
                Text(selection ?? title)
                    .font(.subheadline.weight(selection == nil ? .regular : .semibold))
                Image(systemName: "chevron.down")
                    .font(.caption2.weight(.semibold))
            }
            .foregroundStyle(selection == nil ? Color.wlSecondary : Color.wlAccent)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(selection == nil ? Color.wlSurface : Color.wlAccentSoft, in: Capsule())
            .overlay(Capsule().strokeBorder(selection == nil ? Color.wlHairline : Color.wlAccent, lineWidth: 1))
        }
    }
}
