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
}
