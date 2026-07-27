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

    // MARK: - resolveDestination
    //
    // `resolveDestination` is the routing decision that used to live,
    // untestable, in `FamilyView.navigateToPendingOwnerIfPossible`. Pulling it
    // into `OpenTarget` doesn't make SwiftUI testable — it shrinks the
    // untested surface down to a thin binding (`if let user = ... { path =
    // ...; consumePending() }`) that a reviewer can eyeball, while the actual
    // decision logic gets real coverage here.

    private func user(_ id: Int, _ name: String = "User") -> User {
        User(id: id, name: name, email: "\(name)@example.com", itemCount: nil)
    }

    /// T3: nothing pending → nil, regardless of who's loaded.
    func testResolveDestinationReturnsNilWhenNoPendingTarget() {
        let target = OpenTarget()

        let result = target.resolveDestination(in: [user(1), user(2)])

        XCTAssertNil(result)
    }

    /// T4: the pending owner is in the loaded list → that user, and nothing
    /// changes about the pending state on its own (only a caller's explicit
    /// `consumePending()` should ever clear it).
    func testResolveDestinationReturnsOwnerWhenPresent() {
        let target = OpenTarget()
        let bob = user(2, "Bob")
        target.setPending(itemID: 42, ownerID: 2)

        let result = target.resolveDestination(in: [user(1, "Alice"), bob])

        XCTAssertEqual(result, bob)
    }

    /// T5: the pending owner is NOT in the loaded list yet (still loading, or
    /// an unknown/stale id) → nil, AND the target must survive untouched.
    /// This is the cold-launch case: the member list often finishes loading
    /// in a later pass, and only then does the owner show up. If this
    /// function consumed eagerly on a miss, that later pass would find
    /// nothing left to resolve and the intent would silently do nothing —
    /// exactly the bug `OpenTarget` exists to prevent.
    func testResolveDestinationReturnsNilAndLeavesTargetUnconsumedWhenOwnerMissing() {
        let target = OpenTarget()
        target.setPending(itemID: 42, ownerID: 9)

        let result = target.resolveDestination(in: [user(1, "Alice")])

        XCTAssertNil(result)
        XCTAssertEqual(target.pendingItemID, 42)
        XCTAssertEqual(target.pendingOwnerID, 9)
    }
}
