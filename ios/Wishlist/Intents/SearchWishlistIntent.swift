import AppIntents
import WishlistKit

/// Conforms to `.system.searchInApp`, which is explicitly not category-specific
/// — any app that can search its content may adopt it. This is what gives the
/// read side Apple Intelligence discoverability.
@available(iOS 27, *)
@AppIntent(schema: .system.searchInApp)
struct SearchWishlistIntent: AppIntent {
    static let title: LocalizedStringResource = "Search Wishlist"

    @Parameter(title: "Search")
    var criteria: StringSearchCriteria

    func perform() async throws -> some IntentResult & ReturnsValue<[ItemEntity]> {
        let results = try await IntentService.shared.searchItems(matching: criteria.term)
        return .result(value: results)
    }
}
