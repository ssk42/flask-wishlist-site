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

    /// The routing decision behind "open this item": given whatever member
    /// list is currently loaded, which user (if any) should the app navigate
    /// to right now?
    ///
    /// This is deliberately just the decision, not the navigation itself —
    /// pulling it out of `FamilyView` is what makes it unit-testable at all,
    /// since the view layer that used to hold this logic has no test
    /// coverage and SwiftUI gives us no way to add any.
    ///
    /// Returns `nil` when there is no pending target, or when the owner
    /// hasn't shown up in `users` yet (list still loading, or a stale/unknown
    /// id). Deliberately does NOT call `consumePending()` on a `nil` result —
    /// the pending target is left exactly as it was so a later call, once
    /// `users` has loaded, can still resolve it. A caller consumes only on a
    /// non-`nil` result, once it has actually acted on the destination.
    public func resolveDestination(in users: [User]) -> User? {
        guard let pendingOwnerID else { return nil }
        return users.first(where: { $0.id == pendingOwnerID })
    }
}
