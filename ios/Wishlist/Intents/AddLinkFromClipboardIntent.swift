import AppIntents
import UIKit
import WishlistKit

/// "Add my clipboard to my wishlist."
///
/// Reading `UIPasteboard` shows the system's paste confirmation the first time,
/// which is correct — an intent should not silently read the clipboard. Users who
/// want zero friction can instead build a Shortcut that feeds Get Clipboard into
/// `AddWishlistItemIntent`'s `link` parameter.
struct AddLinkFromClipboardIntent: AppIntent {
    static let title: LocalizedStringResource = "Add Link from Clipboard"
    static let description = IntentDescription(
        "Adds the link on your clipboard to your family wishlist.",
        categoryName: "Wishlist"
    )

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        guard let text = UIPasteboard.general.string,
              !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return .result(dialog: "There's nothing on your clipboard.")
        }
        let item = try await IntentService.shared.addFromLink(text)
        return .result(dialog: "Added \(item.description) to your wishlist.")
    }
}
