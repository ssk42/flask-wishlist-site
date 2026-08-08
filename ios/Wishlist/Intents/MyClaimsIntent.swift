import AppIntents
import WishlistKit

/// "What have I claimed?" Read-only, and safe to speak: these are by definition
/// other people's items, never the caller's own.
struct MyClaimsIntent: AppIntent {
    static let title: LocalizedStringResource = "My Claims"
    static let description = IntentDescription(
        "Lists the items you've claimed for other people.",
        categoryName: "Wishlist"
    )

    func perform() async throws -> some IntentResult & ReturnsValue<[ItemEntity]> & ProvidesDialog {
        let claims = try await IntentService.shared.myClaims()
        let dialog: IntentDialog = claims.isEmpty
            ? "You haven't claimed anything yet."
            : "You've claimed \(claims.count) \(claims.count == 1 ? "item" : "items")."
        return .result(value: claims, dialog: dialog)
    }
}
