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

    /// Typed `URL`, not `String`: a URL-producing Shortcuts action (or the
    /// Action button) then wires straight into this parameter instead of the
    /// user having to coerce text, and Shortcuts offers a URL-appropriate
    /// picker. `URL` is a first-class App Intents parameter type.
    ///
    /// Optional so the same intent serves speech (where no link is given),
    /// Shortcuts, and the Action button.
    @Parameter(title: "Link")
    var link: URL?

    static var parameterSummary: some ParameterSummary {
        Summary("Add \(\.$itemName) to my wishlist")
    }

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let trimmedName = itemName.trimmingCharacters(in: .whitespacesAndNewlines)
        // The service takes a string because that is what the API sends; the
        // URL type earns its keep at the parameter boundary, where Shortcuts
        // and the system need to know what kind of value this is.
        let linkString = link?.absoluteString
        let item: Item
        if trimmedName.isEmpty, let linkString, !linkString.isEmpty {
            item = try await IntentService.shared.addFromLink(linkString)
        } else {
            item = try await IntentService.shared.addItem(
                named: trimmedName, url: linkString, price: nil
            )
        }
        return .result(dialog: "Added \(item.description) to your wishlist.")
    }
}
