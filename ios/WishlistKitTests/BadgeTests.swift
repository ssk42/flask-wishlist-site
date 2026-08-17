import XCTest
@testable import WishlistKit

final class BadgeTests: XCTestCase {
    func testValueIsUnreadCount() {
        XCTAssertEqual(Badge.value(unreadCount: 0), 0)
        XCTAssertEqual(Badge.value(unreadCount: 3), 3)
    }

    func testValueCapsAtNinetyNine() {
        XCTAssertEqual(Badge.value(unreadCount: 100), 99)
        XCTAssertEqual(Badge.value(unreadCount: 500), 99)
    }

    func testValueClampsNegative() {
        XCTAssertEqual(Badge.value(unreadCount: -5), 0)
    }
}