import XCTest
@testable import WishlistKit

final class APIClientWriteTests: XCTestCase {
    private let base = URL(string: "http://test.local")!
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }
    private func client() -> APIClient {
        APIClient(baseURL: base, session: StubURLProtocol.session(), tokenProvider: { "tok" })
    }

    func testCreateItemReturnsOwnItem() async throws {
        StubURLProtocol.handler = { req in
            XCTAssertEqual(req.httpMethod, "POST")
            XCTAssertEqual(req.url?.path, "/api/v1/items")
            let body = #"{"item":{"id":9,"description":"Bike","user_id":1}}"#
            return (HTTPURLResponse(url: req.url!, statusCode: 201, httpVersion: nil, headerFields: nil)!, Data(body.utf8))
        }
        let item = try await client().createItem(ItemDraft(description: "Bike"))
        XCTAssertEqual(item.id, 9)
        XCTAssertNil(item.status)
    }

    func testClaimDecodesItemEnvelope() async throws {
        StubURLProtocol.handler = { req in
            XCTAssertEqual(req.httpMethod, "POST")
            XCTAssertEqual(req.url?.path, "/api/v1/items/1/claim")
            let body = #"{"item":{"id":1,"description":"Bike","user_id":2,"status":"Claimed"}}"#
            return (HTTPURLResponse(url: req.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, Data(body.utf8))
        }
        let item = try await client().claim(itemID: 1)
        XCTAssertEqual(item.id, 1)
        XCTAssertEqual(item.status, "Claimed")
    }

    func testClaimConflictThrows() async {
        StubURLProtocol.handler = { req in
            (HTTPURLResponse(url: req.url!, statusCode: 409, httpVersion: nil, headerFields: nil)!,
             Data(#"{"error":"own_item"}"#.utf8))
        }
        do { _ = try await client().claim(itemID: 1); XCTFail("expected throw") }
        catch let APIError.conflict(code) { XCTAssertEqual(code, "own_item") }
        catch { XCTFail("wrong error: \(error)") }
    }

    func testDeleteItemIssuesDeleteToPath() async throws {
        var captured: URLRequest?
        StubURLProtocol.handler = { req in
            captured = req
            return (HTTPURLResponse(url: req.url!, statusCode: 204, httpVersion: nil, headerFields: nil)!, Data())
        }
        try await client().deleteItem(id: 7)
        XCTAssertEqual(captured?.httpMethod, "DELETE")
        XCTAssertEqual(captured?.url?.path, "/api/v1/items/7")
    }

    func testMarkAllNotificationsReadPostsToReadAllPath() async throws {
        var captured: URLRequest?
        StubURLProtocol.handler = { req in
            captured = req
            return (HTTPURLResponse(url: req.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, Data(#"{"ok":true}"#.utf8))
        }
        try await client().markAllNotificationsRead()
        XCTAssertEqual(captured?.httpMethod, "POST")
        XCTAssertEqual(captured?.url?.path, "/api/v1/notifications/read-all")
    }

    func testUpdateItemPartialPatchOmitsNilFields() async throws {
        var captured: URLRequest?
        StubURLProtocol.handler = { req in
            captured = req
            let body = #"{"item":{"id":9,"description":"Bike","user_id":1,"price":42.5}}"#
            return (HTTPURLResponse(url: req.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, Data(body.utf8))
        }
        _ = try await client().updateItem(id: 9, ItemDraft(price: 42.5))
        XCTAssertEqual(captured?.httpMethod, "PATCH")
        XCTAssertEqual(captured?.url?.path, "/api/v1/items/9")
        let sentBody = try JSONSerialization.jsonObject(with: captured!.httpBody!) as! [String: Any]
        XCTAssertEqual(sentBody["price"] as? Double, 42.5)
        XCTAssertNil(sentBody["description"])
        XCTAssertNil(sentBody["link"])
        XCTAssertNil(sentBody["category"])
        XCTAssertEqual(sentBody.count, 1)
    }

    func testFetchMetadataMapsServerKeys() async throws {
        StubURLProtocol.handler = { req in
            XCTAssertEqual(req.url?.path, "/api/v1/metadata")
            let body = #"{"title":"Cool Bike","price":249.99,"image_url":"https://ex.com/b.jpg"}"#
            return (HTTPURLResponse(url: req.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, Data(body.utf8))
        }
        let draft = try await client().fetchMetadata(url: "https://ex.com/bike")
        XCTAssertEqual(draft.description, "Cool Bike")
        XCTAssertEqual(draft.price, 249.99)
        XCTAssertEqual(draft.imageURL, "https://ex.com/b.jpg")
        XCTAssertEqual(draft.link, "https://ex.com/bike")
    }

    func testRegisterDevicePostsToken() async throws {
        var captured: URLRequest?
        StubURLProtocol.handler = { req in
            captured = req
            return (HTTPURLResponse(url: req.url!, statusCode: 201, httpVersion: nil, headerFields: nil)!, Data(#"{"ok":true}"#.utf8))
        }
        try await client().registerDevice(apnsToken: "dead")
        XCTAssertEqual(captured?.url?.path, "/api/v1/devices")
        let body = try JSONSerialization.jsonObject(with: captured!.httpBody!) as! [String: Any]
        XCTAssertEqual(body["apns_token"] as? String, "dead")
        XCTAssertEqual(body["platform"] as? String, "ios")
    }
}
