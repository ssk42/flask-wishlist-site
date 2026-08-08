import XCTest
@testable import WishlistKit

@MainActor
final class MyListViewModelTests: XCTestCase {
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    private func client(_ body: @escaping (URLRequest) -> (Int, String)) -> APIClient {
        StubURLProtocol.handler = { req in
            let (status, json) = body(req)
            return (HTTPURLResponse(url: req.url!, statusCode: status, httpVersion: nil, headerFields: nil)!,
                    Data(json.utf8))
        }
        return APIClient(baseURL: URL(string: "http://t.local")!,
                         session: StubURLProtocol.session(),
                         tokenProvider: { "tok" })
    }

    func testCreatePrependsReturnedItem() async {
        var sentBody: [String: Any]?
        let vm = MyListViewModel(client: client { req in
            if req.httpMethod == "POST" {
                sentBody = req.bodyDict()
                return (201, #"{"item":{"id":99,"description":"New bike","user_id":1}}"#)
            }
            return (200, #"{"items":[]}"#)
        }, userID: 1)
        let ok = await vm.create(ItemDraft(description: "New bike"))
        XCTAssertTrue(ok)
        XCTAssertEqual(vm.items.first?.description, "New bike")
        XCTAssertEqual(sentBody?["description"] as? String, "New bike")
    }

    func testDeleteRemovesItem() async {
        let vm = MyListViewModel(client: client { req in
            if req.httpMethod == "DELETE" { return (200, #"{"ok":true}"#) }
            return (200, #"{"items":[{"id":5,"description":"Old","user_id":1}]}"#)
        }, userID: 1)
        await vm.load()
        XCTAssertEqual(vm.items.count, 1)
        await vm.delete(vm.items[0])
        XCTAssertTrue(vm.items.isEmpty)
    }

    func testCreateValidationErrorSurfacesMessage() async {
        let vm = MyListViewModel(client: client { _ in (400, #"{"errors":["Description is required."]}"#) }, userID: 1)
        let ok = await vm.create(ItemDraft(description: ""))
        XCTAssertFalse(ok)
        XCTAssertEqual(vm.error, "Description is required.")
    }
}

private extension URLRequest {
    /// Reads the JSON body even though Foundation may have converted it to a stream.
    func bodyDict() -> [String: Any]? {
        if let data = httpBody { return try? JSONSerialization.jsonObject(with: data) as? [String: Any] }
        if let stream = httpBodyStream {
            stream.open(); defer { stream.close() }
            var data = Data(); var buf = [UInt8](repeating: 0, count: 4096)
            while stream.hasBytesAvailable {
                let read = stream.read(&buf, maxLength: buf.count)
                if read <= 0 { break }
                data.append(buf, count: read)
            }
            return try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        }
        return nil
    }
}
