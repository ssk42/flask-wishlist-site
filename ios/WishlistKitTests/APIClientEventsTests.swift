import XCTest
@testable import WishlistKit

final class APIClientEventsTests: XCTestCase {
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

    func testEventsEnvelopeDecodesDateCreatorAndCount() async throws {
        // @spec IOS-EVT-001
        var path: String?
        ok(#"{"events":[{"id":1,"name":"Bday","date":"2026-09-10","created_by":{"id":2,"name":"Mom"},"item_count":3}]}"#)
        { path = $0.url?.path }
        let events = try await client().events()
        XCTAssertEqual(path, "/api/v1/events")
        XCTAssertEqual(events.count, 1)
        XCTAssertEqual(events[0].name, "Bday")
        XCTAssertEqual(events[0].itemCount, 3)
        XCTAssertEqual(events[0].createdBy.name, "Mom")
        let comps = Calendar.current.dateComponents([.year, .month, .day], from: events[0].date)
        XCTAssertEqual([comps.year, comps.month, comps.day], [2026, 9, 10])
    }

    func testEventDetailUsesDetailPathAndMasksOwnItems() async throws {
        // @spec IOS-EVT-002
        var path: String?
        ok(#"{"event":{"id":7,"name":"Bday","date":"2026-09-10","created_by":{"id":2,"name":"Mom"},"item_count":2},"items":[{"id":11,"description":"Own gadget","user_id":5,"created_at":null,"updated_at":null},{"id":12,"description":"Their gadget","status":"Claimed","user_id":9,"last_updated_by":{"id":7,"name":"Alex"},"created_at":null,"updated_at":null}]}"#)
        { path = $0.url?.path }
        let detail = try await client().event(id: 7)
        XCTAssertEqual(path, "/api/v1/events/7")
        XCTAssertEqual(detail.event.id, 7)
        XCTAssertEqual(detail.items.count, 2)
        XCTAssertTrue(detail.items[0].isOwn)
        XCTAssertFalse(detail.items[1].isOwn)
    }

    func testEventsThrowsUnauthorizedOn401() async {
        StubURLProtocol.handler = { req in
            (HTTPURLResponse(url: req.url!, statusCode: 401, httpVersion: nil, headerFields: nil)!,
             Data(#"{"error":"unauthorized"}"#.utf8))
        }
        do { _ = try await client().events(); XCTFail("expected throw") }
        catch APIError.unauthorized { /* expected */ }
        catch { XCTFail("wrong error: \(error)") }
    }
}
