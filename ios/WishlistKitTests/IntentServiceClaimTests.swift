import XCTest
@testable import WishlistKit

final class IntentServiceClaimTests: XCTestCase {
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    private func service(_ respond: @escaping (URLRequest) -> (Int, String)) -> IntentService {
        StubURLProtocol.handler = { req in
            let (status, json) = respond(req)
            return (HTTPURLResponse(url: req.url!, statusCode: status, httpVersion: nil, headerFields: nil)!,
                    Data(json.utf8))
        }
        let store = InMemoryTokenStore(); store.save("tok")
        let client = APIClient(baseURL: URL(string: "http://t.local")!,
                               session: StubURLProtocol.session(),
                               tokenProvider: { store.read() })
        return IntentService(client: client, tokenStore: store)
    }

    func testClaimSucceeds() async throws {
        let svc = service { _ in
            (200, #"{"item":{"id":5,"description":"Book","user_id":9,"status":"Claimed"}}"#)
        }
        let item = try await svc.claim(itemID: 5)
        XCTAssertEqual(item.status, "Claimed")
    }

    func testClaimingOwnItemSpeaksTheReason() async {
        let svc = service { _ in (409, #"{"error":"own_item"}"#) }
        do {
            _ = try await svc.claim(itemID: 1)
            XCTFail("expected message")
        } catch IntentError.message(let text) {
            XCTAssertEqual(text, "You can't claim your own item.")
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    func testAlreadyClaimedSpeaksTheReason() async {
        let svc = service { _ in (409, #"{"error":"not_available"}"#) }
        do {
            _ = try await svc.claim(itemID: 1)
            XCTFail("expected message")
        } catch IntentError.message(let text) {
            XCTAssertEqual(text, "Someone already claimed this.")
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    func testMyClaimsReturnsEntities() async throws {
        let svc = service { req in
            req.url!.path.hasSuffix("/users")
                ? (200, #"{"users":[{"id":9,"name":"Mom","email":"m@x.com"}]}"#)
                : (200, #"{"items":[{"id":5,"description":"Book","user_id":9,"status":"Claimed"}]}"#)
        }
        let claims = try await svc.myClaims()
        XCTAssertEqual(claims.map(\.name), ["Book"])
        XCTAssertEqual(claims.first?.ownerName, "Mom")
    }
}
