import XCTest
@testable import WishlistKit

final class SmokeTests: XCTestCase {
    func testVersion() {
        XCTAssertEqual(WishlistKit.version, "1.0")
    }
}
