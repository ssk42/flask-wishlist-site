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
            // Names the owner too: mis-resolution happens between similarly
            // named items, and on HomePod or CarPlay this spoken line is the
            // only thing standing between a misheard name and a wrong claim.
            result: .result(dialog: "Claim \(target.name) for \(target.ownerName ?? "them")?")
        )
        let item = try await IntentService.shared.claim(itemID: target.id)
        return .result(dialog: "Claimed \(item.description).")
    }
}
