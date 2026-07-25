import Foundation

/// Single source of truth for the backend location, shared by the app and the
/// Share Extension (separate processes — duplicating this would let them drift).
public enum WishlistAPI {
    /// Local Flask during development. Port 8000 rather than 5000 because macOS
    /// AirPlay Receiver occupies 5000. Swap for the deployed URL to ship.
    public static let defaultBaseURL = URL(string: "http://localhost:8000")!

    /// Keychain access group shared between the app and its extensions.
    public static let sharedKeychainGroup = "com.reitz.wishlist.shared"
}
