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
