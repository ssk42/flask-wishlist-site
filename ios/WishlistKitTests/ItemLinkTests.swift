import XCTest
@testable import WishlistKit

final class ItemLinkTests: XCTestCase {
    func testParsesItemLinks() {
        // @spec IOS-ACT-011
        XCTAssertEqual(ItemLink.itemID(from: "/items/42"), 42)
        XCTAssertEqual(ItemLink.itemID(from: "https://gifts.example/items/7"), 7)
    }

    func testRejectsNonItemLinks() {
        // @spec IOS-ACT-011
        XCTAssertNil(ItemLink.itemID(from: ""))
        XCTAssertNil(ItemLink.itemID(from: "/activity"))
        XCTAssertNil(ItemLink.itemID(from: "/items/abc"))
    }
}
