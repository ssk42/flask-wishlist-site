import XCTest
@testable import WishlistKit

/// `OpenTarget` is the fix for a defect where "open the cashmere blanket in
/// Wishlist" posted a `NotificationCenter` message that (a) only carried an
/// item id, discarded on the receiving end, and (b) was lost outright on a
/// cold launch because `NotificationCenter` never buffers for a subscriber
/// that doesn't exist yet. These tests exercise the coordinator in isolation
/// — no view, no notification — so the routing itself is addressable.
@MainActor
final class OpenTargetTests: XCTestCase {
    /// T1: setting a target leaves the coordinator holding exactly the ids
    /// that were set. This is the warm-path defect: the old `RootTabView`
    /// received a notification but its `onReceive` closure ignored `userInfo`
    /// entirely, so neither id survived to be acted on.
    func testSettingATargetIsHeldExactly() {
        let target = OpenTarget()

        target.setPending(itemID: 42, ownerID: 9)

        XCTAssertEqual(target.pendingItemID, 42)
        XCTAssertEqual(target.pendingOwnerID, 9)
    }

    /// T2: a target set before any consumer exists is still correct once one
    /// finally reads it. This is the cold-launch defect: `perform()` can run
    /// (and, in the old code, post to `NotificationCenter`) before
    /// `RootTabView` is even mounted to subscribe, so the payload vanished
    /// for good. `OpenTarget` must not have any equivalent "nobody was
    /// listening" failure mode — including an eager auto-clear that fires
    /// before a real consumer arrives.
    func testTargetSetBeforeConsumerExistsSurvives() {
        let target = OpenTarget()

        // The intent fires here — no view, no consumer, nothing subscribed.
        target.setPending(itemID: 42, ownerID: 9)

        // Time passes (e.g. LoginView is on screen). Nothing has consumed the
        // target yet, so a non-destructive read must still see it.
        XCTAssertEqual(target.pendingItemID, 42)
        XCTAssertEqual(target.pendingOwnerID, 9)

        // A consumer finally attaches (e.g. FamilyView, once its member list
        // has loaded) and reads-and-clears the target.
        let consumed = target.consumePending()

        XCTAssertEqual(consumed?.itemID, 42)
        XCTAssertEqual(consumed?.ownerID, 9)

        // Consumed exactly once — no stale target left to replay.
        XCTAssertNil(target.pendingItemID)
        XCTAssertNil(target.pendingOwnerID)
    }
}
