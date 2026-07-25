import AppIntents
import WishlistKit

/// "Add AirPods Pro to my wishlist."
///
/// Custom rather than schema-conformant: the only schema offering "create an
/// item in a list" is `.reminders.createReminder`, and adopting it would enter
/// this app into the pool Siri picks from for real reminders. See the design
/// spec for the full reasoning.
struct AddWishlistItemIntent: AppIntent {
    static let title: LocalizedStringResource = "Add to Wishlist"
    static let description = IntentDescription(
        "Adds an item to your family wishlist.",
        categoryName: "Wishlist"
    )

    /// Requesting a value means Siri prompts for it rather than failing when
    /// the phrase carries no item name.
    @Parameter(title: "Item", requestValueDialog: "What should I add?")
    var itemName: String

    /// Optional so the same intent serves Shortcuts and the Action button,
    /// where a URL is passed instead of spoken.
    @Parameter(title: "Link")
    var link: String?

    static var parameterSummary: some ParameterSummary {
        Summary("Add \(\.$itemName) to my wishlist")
    }

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let trimmedName = itemName.trimmingCharacters(in: .whitespacesAndNewlines)
        let item: Item
        if trimmedName.isEmpty, let link, !link.isEmpty {
            item = try await IntentService.shared.addFromLink(link)
        } else {
            item = try await IntentService.shared.addItem(
                named: trimmedName, url: link, price: nil
            )
        }
        return .result(dialog: "Added \(item.description) to your wishlist.")
    }
}
