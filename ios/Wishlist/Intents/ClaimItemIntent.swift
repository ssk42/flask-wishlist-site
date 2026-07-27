import AppIntents
import WishlistKit

/// "Claim the blanket." On iOS 27, also "claim this" via on-screen awareness.
///
/// Confirmation is required: claiming changes what other people see, and a
/// misheard item name would otherwise commit silently.
struct ClaimItemIntent: AppIntent {
    static let title: LocalizedStringResource = "Claim Item"
    static let description = IntentDescription(
        "Claims a family member's wishlist item so others know it's taken.",
        categoryName: "Wishlist"
    )

    @Parameter(title: "Item")
    var target: ItemEntity

    static var parameterSummary: some ParameterSummary {
        Summary("Claim \(\.$target)")
    }

    func perform() async throws -> some IntentResult & ProvidesDialog {
        try await requestConfirmation(
            result: .result(dialog: "Claim \(target.name)?")
        )
        let item = try await IntentService.shared.claim(itemID: target.id)
        return .result(dialog: "Claimed \(item.description).")
    }
}
