import Foundation

/// Single source of truth for the backend location, shared by the app and the
/// Share Extension (separate processes — duplicating this would let them drift).
public enum WishlistAPI {
    /// Deployed backend. HTTPS, so no App Transport Security exception is needed.
    public static let productionBaseURL = URL(string: "https://gifts.stevereitz.dev")!

    /// Local Flask. Port 8000 rather than 5000 because macOS AirPlay Receiver
    /// occupies 5000. Reaching this requires the localhost ATS exception that
    /// both targets' Info.plists carry.
    public static let localBaseURL = URL(string: "http://localhost:8000")!

    /// Resolved backend. Set a `WLAPIBaseURL` string in the target's Info.plist
    /// to override — that way pointing a build at a local server (or a staging
    /// host) is a plist change, not a code change, and both the app and the
    /// extension pick it up.
    public static var defaultBaseURL: URL {
        if let raw = Bundle.main.object(forInfoDictionaryKey: "WLAPIBaseURL") as? String,
           !raw.isEmpty,
           let url = URL(string: raw) {
            return url
        }
        return productionBaseURL
    }

    /// Keychain access group shared between the app and its extensions.
    public static let sharedKeychainGroup = "com.reitz.wishlist.shared"
}
