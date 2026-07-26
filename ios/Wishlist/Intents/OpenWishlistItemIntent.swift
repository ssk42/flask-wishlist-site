import AppIntents
import Foundation
import WishlistKit

/// Conforms to `.system.open` so "open the blanket in Wishlist" works and pairs
/// with search results.
///
/// `OpenIntent` supplies a default `perform()`, but this one is overridden so the
/// app can route to the right screen rather than only coming to the foreground.
@available(iOS 27, *)
@AppIntent(schema: .system.open)
struct OpenWishlistItemIntent: AppIntent {
    static let title: LocalizedStringResource = "Open Wishlist Item"
    static let openAppWhenRun: Bool = true

    @Parameter(title: "Item")
    var target: ItemEntity

    @MainActor
    func perform() async throws -> some IntentResult {
        NotificationCenter.default.post(
            name: .wishlistOpenItem, object: nil, userInfo: ["itemID": target.id]
        )
        return .result()
    }
}

public extension Notification.Name {
    static let wishlistOpenItem = Notification.Name("WishlistOpenItem")
}
