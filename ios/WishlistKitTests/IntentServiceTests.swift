import XCTest
@testable import WishlistKit

final class IntentServiceTests: XCTestCase {
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    private func service(token: String? = "tok",
                         _ respond: @escaping (URLRequest) -> (Int, String) = { _ in (200, "{}") })
        -> IntentService {
        StubURLProtocol.handler = { req in
            let (status, json) = respond(req)
            return (HTTPURLResponse(url: req.url!, statusCode: status, httpVersion: nil, headerFields: nil)!,
                    Data(json.utf8))
        }
        let store = InMemoryTokenStore()
        if let token { store.save(token) }
        let client = APIClient(baseURL: URL(string: "http://t.local")!,
                               session: StubURLProtocol.session(),
                               tokenProvider: { store.read() })
        return IntentService(client: client, tokenStore: store)
    }

    func testAddItemPostsAndReturnsItem() async throws {
        var body: [String: Any]?
        let svc = service { req in
            body = Self.jsonBody(req)
            return (201, #"{"item":{"id":9,"description":"AirPods Pro","user_id":1}}"#)
        }

        let item = try await svc.addItem(named: "AirPods Pro", url: nil, price: nil)

        XCTAssertEqual(item.description, "AirPods Pro")
        XCTAssertEqual(body?["description"] as? String, "AirPods Pro")
    }

    func testAddItemWithoutTokenFailsBeforeAnyNetworkCall() async {
        var called = false
        let svc = service(token: nil) { _ in called = true; return (201, "{}") }

        do {
            _ = try await svc.addItem(named: "AirPods", url: nil, price: nil)
            XCTFail("expected notSignedIn")
        } catch IntentError.notSignedIn {
            XCTAssertFalse(called, "must not hit the network when signed out")
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    func testUnauthorizedMidFlightBecomesNotSignedIn() async {
        let svc = service { _ in (401, #"{"error":"unauthorized"}"#) }

        do {
            _ = try await svc.addItem(named: "AirPods", url: nil, price: nil)
            XCTFail("expected notSignedIn")
        } catch IntentError.notSignedIn {
            // correct: a revoked token reads the same as being signed out
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    func testValidationErrorSurfacesServerMessage() async {
        let svc = service { _ in (400, #"{"errors":["Description is required."]}"#) }

        do {
            _ = try await svc.addItem(named: " ", url: nil, price: nil)
            XCTFail("expected message")
        } catch IntentError.message(let text) {
            XCTAssertEqual(text, "Description is required.")
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    func testAddFromLinkPrefillsDescriptionFromMetadata() async throws {
        var paths: [String] = []
        var createBody: [String: Any]?
        let svc = service { req in
            paths.append(req.url?.path ?? "")
            if req.url?.path.contains("metadata") == true {
                return (200, #"{"title":"Cashmere Blanket","price":89.0,"link":"https://shop.test/b"}"#)
            }
            createBody = Self.jsonBody(req)
            return (201, #"{"item":{"id":4,"description":"Cashmere Blanket","user_id":1}}"#)
        }

        let item = try await svc.addFromLink("https://shop.test/b")

        XCTAssertEqual(item.description, "Cashmere Blanket")
        XCTAssertTrue(paths.contains { $0.contains("metadata") }, "should fetch metadata first")
        XCTAssertEqual(createBody?["description"] as? String, "Cashmere Blanket",
                       "the metadata title should have been merged into the create-item request body")
    }

    func testAddFromLinkFallsBackToURLWhenMetadataFails() async throws {
        let svc = service { req in
            if req.url?.path.contains("metadata") == true {
                return (502, #"{"error":"fetch_failed"}"#)
            }
            return (201, #"{"item":{"id":5,"description":"https://shop.test/b","user_id":1}}"#)
        }

        // A dead scraper must not block saving the link — it is still useful.
        let item = try await svc.addFromLink("https://shop.test/b")

        XCTAssertEqual(item.description, "https://shop.test/b")
    }

    func testAddFromLinkRejectsNonURLText() async {
        let svc = service { _ in (201, "{}") }

        do {
            _ = try await svc.addFromLink("just some words")
            XCTFail("expected message")
        } catch IntentError.message(let text) {
            XCTAssertEqual(text, "That doesn't look like a link.")
        } catch {
            XCTFail("wrong error: \(error)")
        }
    }

    static func jsonBody(_ req: URLRequest) -> [String: Any]? {
        if let data = req.httpBody {
            return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        }
        guard let stream = req.httpBodyStream else { return nil }
        stream.open(); defer { stream.close() }
        var data = Data(); var buf = [UInt8](repeating: 0, count: 4096)
        while stream.hasBytesAvailable {
            let read = stream.read(&buf, maxLength: buf.count)
            if read <= 0 { break }
            data.append(buf, count: read)
        }
        return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    }
}
