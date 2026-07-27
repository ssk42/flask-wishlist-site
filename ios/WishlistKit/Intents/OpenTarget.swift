import Foundation
import Observation

/// Hands off "open this item" navigation from an App Intent to the SwiftUI
/// layer, without relying on `NotificationCenter`.
///
/// `NotificationCenter` does not buffer posts for future subscribers: on a
/// cold launch the intent's `perform()` can run — and post — before
/// `RootTabView` exists to receive it, and the notification is lost for good.
/// `OpenTarget` is a plain object with stored properties instead, so a target
/// set before any view is mounted is simply sitting there, unchanged, whenever
/// a view finally looks.
///
/// Deliberately usable at the iOS 17 floor: only the two schema-conformant
/// intents that populate it are gated to iOS 27, not this coordinator or the
/// views that read it.
@MainActor
@Observable
public final class OpenTarget {
    /// Shared instance used by the app's intents and views. Tests should
    /// construct their own `OpenTarget()` instead, so cases don't leak state
    /// into each other.
    public static let shared = OpenTarget()

    public private(set) var pendingItemID: Int?
    public private(set) var pendingOwnerID: Int?

    public init() {}

    /// Records where the app should navigate. Called by an intent's
    /// `perform()`, which may run well before any view is on screen.
    public func setPending(itemID: Int, ownerID: Int) {
        pendingItemID = itemID
        pendingOwnerID = ownerID
    }

    /// Reads and clears the pending target in one step, for a view that is
    /// ready to act on it right now. Returns `nil` if nothing is pending.
    @discardableResult
    public func consumePending() -> (itemID: Int, ownerID: Int)? {
        guard let itemID = pendingItemID, let ownerID = pendingOwnerID else { return nil }
        pendingItemID = nil
        pendingOwnerID = nil
        return (itemID, ownerID)
    }
}
