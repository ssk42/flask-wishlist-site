import AppIntents
import Foundation

/// Errors an intent can surface to Siri. Conforming to
/// `CustomLocalizedStringResourceConvertible` is what lets Siri *speak* the
/// reason instead of a generic failure.
public enum IntentError: Error, CustomLocalizedStringResourceConvertible {
    /// No token, or the token was rejected. Same message either way — from the
    /// user's point of view "signed out" and "token expired" are the same fix.
    case notSignedIn
    /// A reason from the server or a business rule, already phrased for speech.
    case message(String)

    public var localizedStringResource: LocalizedStringResource {
        switch self {
        case .notSignedIn:
            return "Open Wishlist and log in first."
        case .message(let text):
            return LocalizedStringResource(stringLiteral: text)
        }
    }
}

/// Human-readable copy for the API's conflict codes, shared by every surface.
///
/// Lives in one place deliberately: this used to be duplicated in
/// `IntentService` and `MemberItemsViewModel` with drifting defaults, and
/// because neither copy listed `not_claimer` — which `services/item_service.py`
/// really does raise — unclaiming someone else's claim fell through to the
/// generic fallback instead of saying why.
///
/// Keep in sync with `ItemActionError` codes in `services/item_service.py`.
public enum ConflictCopy {
    /// @spec IOS-GIFT-004
    public static func friendly(_ code: String) -> String {
        switch code {
        case "own_item": "You can't claim your own item."
        case "not_available": "Someone already claimed this."
        case "not_claimer": "You can't unclaim this — someone else claimed it."
        case "already_purchased": "This item is already purchased."
        case "claimed_by_other": "This item is claimed by someone else."
        default: "That action isn't allowed."
        }
    }
}
