import XCTest
@testable import WishlistKit

final class ModelDecodingTests: XCTestCase {
    private func decode<T: Decodable>(_ type: T.Type, _ json: String) throws -> T {
        try JSONDecoder().decode(T.self, from: Data(json.utf8))
    }

    func testDecodesUserWithItemCount() throws {
        let user = try decode(User.self, #"{"id":1,"name":"Alex","email":"a@x.com","item_count":3}"#)
        XCTAssertEqual(user.id, 1)
        XCTAssertEqual(user.name, "Alex")
        XCTAssertEqual(user.itemCount, 3)
    }

    func testDecodesUserWithoutItemCount() throws {
        let user = try decode(User.self, #"{"id":2,"name":"Sam","email":"s@x.com"}"#)
        XCTAssertNil(user.itemCount)
    }

    func testOwnItemHasNilStatus() throws {
        // @spec IOS-NET-004
        // Server omits status/last_updated_by for the viewer's own items.
        let item = try decode(Item.self, #"{"id":10,"description":"Bike","price":99.5,"user_id":1}"#)
        XCTAssertNil(item.status)
        XCTAssertNil(item.lastUpdatedBy)
        XCTAssertEqual(item.price, 99.5)
    }

    func testOthersItemHasStatusAndClaimer() throws {
        let json = #"{"id":11,"description":"Book","user_id":2,"status":"Claimed","last_updated_by":{"id":1,"name":"Alex"}}"#
        let item = try decode(Item.self, json)
        XCTAssertEqual(item.status, "Claimed")
        XCTAssertEqual(item.lastUpdatedBy?.name, "Alex")
    }

    func testDecodesNotification() throws {
        let json = #"{"id":5,"message":"hi","link":"/items","is_read":false,"created_at":"2026-01-01T00:00:00+00:00"}"#
        let n = try decode(WishlistNotification.self, json)
        XCTAssertEqual(n.message, "hi")
        XCTAssertFalse(n.isRead)
    }
}
