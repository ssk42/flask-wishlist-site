import XCTest
@testable import WishlistKit

final class ItemEntityTests: XCTestCase {
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    private func decodeItem(_ json: String) throws -> Item {
        try JSONDecoder().decode(Item.self, from: Data(json.utf8))
    }

    func testOwnItemCarriesNoStatus() throws {
        // Server omits status for the caller's own items.
        let item = try decodeItem(#"{"id":1,"description":"Bike","user_id":7}"#)
        let entity = ItemEntity(item: item, ownerName: nil)

        XCTAssertNil(entity.status)
        XCTAssertTrue(item.isOwn)
    }

    func testOthersItemKeepsStatus() throws {
        let item = try decodeItem(#"{"id":2,"description":"Book","user_id":9,"status":"Claimed"}"#)
        let entity = ItemEntity(item: item, ownerName: "Mom")

        XCTAssertEqual(entity.status, "Claimed")
        XCTAssertEqual(entity.ownerName, "Mom")
    }

    func testSpokenDescriptionNeverLeaksOwnItemStatus() throws {
        // The display representation is what Siri reads aloud. For an own item it
        // must not imply anything about claims — that is the whole invariant.
        //
        // Siri can voice both the title AND the subtitle of a DisplayRepresentation,
        // and status (when present) lives in the subtitle here — so the "spoken"
        // string under test must include both, not just the title. A version of
        // this test that checked title alone would pass even if the subtitle leaked
        // status, defeating the point of the test.
        let own = ItemEntity(item: try decodeItem(#"{"id":1,"description":"Bike","user_id":7}"#),
                             ownerName: nil)
        let representation = own.displayRepresentation
        let spoken = "\(representation.title) \(representation.subtitle.map { "\($0)" } ?? "")"

        XCTAssertTrue(spoken.contains("Bike"))
        for banned in ["Claimed", "Purchased", "Available"] {
            XCTAssertFalse(spoken.contains(banned), "own item leaked \(banned)")
        }
    }

    func testSearchReturnsMatchingEntities() async throws {
        StubURLProtocol.handler = { req in
            let json = req.url!.path.hasSuffix("/users")
                ? #"{"users":[{"id":9,"name":"Mom","email":"m@x.com"}]}"#
                : #"{"items":[{"id":2,"description":"Cashmere throw","user_id":9,"status":"Available"}]}"#
            return (HTTPURLResponse(url: req.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!,
                    Data(json.utf8))
        }
        let store = InMemoryTokenStore(); store.save("tok")
        let client = APIClient(baseURL: URL(string: "http://t.local")!,
                               session: StubURLProtocol.session(),
                               tokenProvider: { store.read() })
        let svc = IntentService(client: client, tokenStore: store)

        let results = try await svc.searchItems(matching: "cashmere")

        XCTAssertEqual(results.count, 1)
        XCTAssertEqual(results.first?.name, "Cashmere throw")
        XCTAssertEqual(results.first?.ownerName, "Mom")
    }
}
