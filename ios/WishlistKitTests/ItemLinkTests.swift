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

    func testParsesEventLinks() {
        // @spec IOS-EVT-013
        XCTAssertEqual(ItemLink.eventID(from: "/events/7"), 7)
        XCTAssertEqual(ItemLink.eventID(from: "https://gifts.example/events/42"), 42)
    }

    func testRejectsNonEventLinks() {
        // @spec IOS-EVT-013
        XCTAssertNil(ItemLink.eventID(from: ""))
        XCTAssertNil(ItemLink.eventID(from: "/items/42"))
        XCTAssertNil(ItemLink.eventID(from: "/events/abc"))
    }
}
