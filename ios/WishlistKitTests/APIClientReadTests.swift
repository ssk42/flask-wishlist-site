import XCTest
@testable import WishlistKit

final class APIClientReadTests: XCTestCase {
    private let base = URL(string: "http://test.local")!
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }
    private func client() -> APIClient {
        APIClient(baseURL: base, session: StubURLProtocol.session(), tokenProvider: { "tok" })
    }
    private func ok(_ body: String, capture: ((URLRequest) -> Void)? = nil) {
        StubURLProtocol.handler = { req in
            capture?(req)
            return (HTTPURLResponse(url: req.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, Data(body.utf8))
        }
    }

    func testUsers() async throws {
        ok(#"{"users":[{"id":1,"name":"Alex","email":"a@x.com","item_count":2}]}"#)
        let users = try await client().users()
        XCTAssertEqual(users.map(\.name), ["Alex"])
    }

    func testItemsBuildsQuery() async throws {
        // @spec IOS-NET-003
        var url: URL?
        ok(#"{"items":[]}"#) { url = $0.url }
        _ = try await client().items(userID: 3, status: "Available", category: "Tech", query: "bike")
        let comps = URLComponents(url: url!, resolvingAgainstBaseURL: false)!
        let q = Dictionary(uniqueKeysWithValues: (comps.queryItems ?? []).map { ($0.name, $0.value) })
        XCTAssertEqual(q["user_id"], "3")
        XCTAssertEqual(q["status"], "Available")
        XCTAssertEqual(q["category"], "Tech")
        XCTAssertEqual(q["q"], "bike")
    }

    func testNotificationsEnvelope() async throws {
        ok(#"{"notifications":[{"id":1,"message":"hi","link":"/","is_read":false,"created_at":null}],"unread_count":4}"#)
        let result = try await client().notifications()
        XCTAssertEqual(result.unreadCount, 4)
        XCTAssertEqual(result.items.count, 1)
    }

    func testMeReturnsProfile() async throws {
        var path: String?
        ok(#"{"user":{"id":7,"name":"Alex","email":"a@x.com"}}"#) { path = $0.url?.path }
        let user = try await client().me()
        XCTAssertEqual(path, "/api/v1/me")
        XCTAssertEqual(user.id, 7)
        XCTAssertEqual(user.name, "Alex")
    }

    func testItemByIDDecodesItemAndOwner() async throws {
        var path: String?
        ok(#"{"item":{"id":42,"description":"Their gadget","price":42.5,"status":"Claimed","user_id":9,"last_updated_by":{"id":7,"name":"Alex"},"created_at":null,"updated_at":null},"owner":{"id":9,"name":"Other","email":"other@x.com"}}"#)
        { path = $0.url?.path }
        let result = try await client().item(id: 42)
        XCTAssertEqual(path, "/api/v1/items/42")
        XCTAssertEqual(result.item.id, 42)
        XCTAssertEqual(result.item.status, "Claimed")
        XCTAssertEqual(result.owner.id, 9)
        XCTAssertEqual(result.owner.name, "Other")
    }

    func testItemByIDThrowsUnauthorizedOn401() async {
        StubURLProtocol.handler = { req in
            (HTTPURLResponse(url: req.url!, statusCode: 401, httpVersion: nil, headerFields: nil)!,
             Data(#"{"error":"unauthorized"}"#.utf8))
        }
        do { _ = try await client().item(id: 1); XCTFail("expected throw") }
        catch APIError.unauthorized { /* expected */ }
        catch { XCTFail("wrong error: \(error)") }
    }
}
