import XCTest
@testable import WishlistKit

@MainActor
final class ShareItemViewModelTests: XCTestCase {
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    private func client(_ respond: @escaping (URLRequest) -> (Int, String)) -> APIClient {
        StubURLProtocol.handler = { req in
            let (status, json) = respond(req)
            return (HTTPURLResponse(url: req.url!, statusCode: status, httpVersion: nil, headerFields: nil)!,
                    Data(json.utf8))
        }
        return APIClient(baseURL: URL(string: "http://t.local")!,
                         session: StubURLProtocol.session(),
                         tokenProvider: { "tok" })
    }

    // MARK: prefill

    func testPrefillMapsMetadataAndKeepsSharedURL() async {
        let vm = ShareItemViewModel(client: client { _ in
            (200, #"{"title":"Cashmere throw","price":120.0,"image_url":"https://ex.com/t.jpg"}"#)
        })

        await vm.prefill(urlString: "https://shop.example/throw?ref=share")

        XCTAssertEqual(vm.draft.description, "Cashmere throw")
        XCTAssertEqual(vm.draft.price, 120.0)
        XCTAssertEqual(vm.draft.imageURL, "https://ex.com/t.jpg")
        XCTAssertEqual(vm.draft.link, "https://shop.example/throw?ref=share")
        XCTAssertNil(vm.error)
        XCTAssertTrue(vm.canSubmit)
    }

    func testPrefillFailureStillLeavesUsableForm() async {
        // Metadata lookup fails (site blocked it) — the link must survive so the
        // user can just type a description and save.
        let vm = ShareItemViewModel(client: client { _ in (502, #"{"error":"fetch_failed"}"#) })

        await vm.prefill(urlString: "https://shop.example/x")

        XCTAssertEqual(vm.draft.link, "https://shop.example/x")
        XCTAssertNil(vm.error)          // best-effort: no scary message
        XCTAssertFalse(vm.needsLogin)
        XCTAssertFalse(vm.canSubmit)    // needs a description first
    }

    func testPrefillWithoutTokenAsksUserToLogIn() async {
        let vm = ShareItemViewModel(client: client { _ in (401, #"{"error":"unauthorized"}"#) })

        await vm.prefill(urlString: "https://shop.example/x")

        XCTAssertTrue(vm.needsLogin)
        XCTAssertEqual(vm.error, "Open the Wishlist app and log in first.")
    }

    // MARK: submit

    func testSubmitPostsDraft() async {
        var body: [String: Any]?
        let vm = ShareItemViewModel(client: client { req in
            if req.httpMethod == "POST", req.url?.path == "/api/v1/items" {
                body = Self.jsonBody(req)
                return (201, #"{"item":{"id":7,"description":"Cashmere throw","user_id":1}}"#)
            }
            return (200, #"{"title":"Cashmere throw","price":120.0}"#)
        })
        await vm.prefill(urlString: "https://shop.example/throw")

        let ok = await vm.submit()

        XCTAssertTrue(ok)
        XCTAssertEqual(body?["description"] as? String, "Cashmere throw")
        XCTAssertEqual(body?["link"] as? String, "https://shop.example/throw")
        XCTAssertNil(vm.error)
    }

    func testSubmitRefusesEmptyDescriptionWithoutCallingAPI() async {
        var called = false
        let vm = ShareItemViewModel(client: client { _ in called = true; return (201, "{}") })
        vm.draft.link = "https://shop.example/x"

        let ok = await vm.submit()

        XCTAssertFalse(ok)
        XCTAssertFalse(called, "should not hit the network with an empty description")
        XCTAssertEqual(vm.error, "Add a short description.")
    }

    func testSubmitSurfacesValidationError() async {
        let vm = ShareItemViewModel(client: client { _ in
            (400, #"{"errors":["Link must be a valid http or https URL."]}"#)
        })
        vm.draft.description = "Something"

        let ok = await vm.submit()

        XCTAssertFalse(ok)
        XCTAssertEqual(vm.error, "Link must be a valid http or https URL.")
    }

    func testSubmitWithoutTokenAsksUserToLogIn() async {
        let vm = ShareItemViewModel(client: client { _ in (401, #"{"error":"unauthorized"}"#) })
        vm.draft.description = "Something"

        let ok = await vm.submit()

        XCTAssertFalse(ok)
        XCTAssertTrue(vm.needsLogin)
    }

    /// Foundation may convert httpBody to a stream before a URLProtocol sees it.
    private static func jsonBody(_ req: URLRequest) -> [String: Any]? {
        if let data = req.httpBody {
            return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        }
        guard let stream = req.httpBodyStream else { return nil }
        stream.open(); defer { stream.close() }
        var data = Data(); var buffer = [UInt8](repeating: 0, count: 4096)
        while stream.hasBytesAvailable {
            let read = stream.read(&buffer, maxLength: buffer.count)
            if read <= 0 { break }
            data.append(buffer, count: read)
        }
        return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    }
}
