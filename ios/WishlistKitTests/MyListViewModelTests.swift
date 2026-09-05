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
        // @spec IOS-CUR-002
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
        // @spec IOS-CUR-001, IOS-CUR-004
        let vm = MyListViewModel(client: client { req in
            if req.httpMethod == "DELETE" { return (200, #"{"ok":true}"#) }
            return (200, #"{"items":[{"id":5,"description":"Old","user_id":1}]}"#)
        }, userID: 1)
        await vm.load()
        XCTAssertEqual(vm.items.count, 1)
        await vm.delete(vm.items[0])
        XCTAssertTrue(vm.items.isEmpty)
    }

    func testQueryFiltersByDescriptionAndCategory() async {
        // @spec IOS-CUR-009
        let vm = MyListViewModel(client: client { _ in
            (200, #"{"items":[{"id":1,"description":"Stand mixer","category":"Kitchen","user_id":1},{"id":2,"description":"Novel","category":"Books","user_id":1}]}"#)
        }, userID: 1)
        await vm.load()
        vm.query = "kitchen"
        XCTAssertEqual(vm.filteredItems.map(\.id), [1])
        vm.query = "NOVEL"
        XCTAssertEqual(vm.filteredItems.map(\.id), [2])
        vm.query = ""
        XCTAssertEqual(vm.filteredItems.map(\.id), [1, 2])
        vm.query = "nope"
        XCTAssertTrue(vm.filteredItems.isEmpty)
    }

    func testUserIDFromState() {
        // @spec IOS-CUR-010
        XCTAssertEqual(MyListViewModel.userID(from: .loggedIn(User(id: 7, name: "Alex", email: "a@x.com", itemCount: 0))), 7)
        XCTAssertNil(MyListViewModel.userID(from: .loggedOut))
    }

    func testPriorityAndCategoryFiltersAndWithQuery() async {
        // @spec IOS-CUR-011
        let vm = MyListViewModel(client: client { _ in
            (200, #"{"items":[{"id":1,"description":"Stand mixer","category":"Kitchen","priority":"High","user_id":1},{"id":2,"description":"Novel","category":"Books","priority":"Low","user_id":1},{"id":3,"description":"Socks","user_id":1}]}"#)
        }, userID: 1)
        await vm.load()
        vm.selectedPriority = "High"
        XCTAssertEqual(vm.filteredItems.map(\.id), [1])
        vm.selectedPriority = nil
        vm.selectedCategory = "Books"
        XCTAssertEqual(vm.filteredItems.map(\.id), [2])
        vm.query = "mixer"
        vm.selectedCategory = nil
        vm.selectedPriority = "High"
        XCTAssertEqual(vm.filteredItems.map(\.id), [1])
        vm.query = "novel"
        XCTAssertTrue(vm.filteredItems.isEmpty)
        XCTAssertEqual(vm.items.count, 3)
    }

    func testNilFieldsMatchOnlyAll() async {
        // @spec IOS-CUR-011
        let vm = MyListViewModel(client: client { _ in
            (200, #"{"items":[{"id":1,"description":"Stand mixer","category":"Kitchen","priority":"High","user_id":1},{"id":3,"description":"Socks","user_id":1}]}"#)
        }, userID: 1)
        await vm.load()
        vm.selectedCategory = "Kitchen"
        XCTAssertEqual(vm.filteredItems.map(\.id), [1])
        vm.selectedCategory = nil
        vm.selectedPriority = "Low"
        XCTAssertTrue(vm.filteredItems.isEmpty)
        XCTAssertEqual(vm.items.count, 2)
    }

    func testCreateValidationErrorSurfacesMessage() async {
        let vm = MyListViewModel(client: client { _ in (400, #"{"errors":["Description is required."]}"#) }, userID: 1)
        let ok = await vm.create(ItemDraft(description: ""))
        XCTAssertFalse(ok)
        XCTAssertEqual(vm.error, "Description is required.")
    }

    func testPrefillMapsMetadataAndKeepsGivenLink() async {
        let vm = MyListViewModel(client: client { _ in
            (200, #"{"title":"A lovely bike","price":42.5,"image_url":"https://img/x.png"}"#)
        }, userID: 1)
        let draft = await vm.prefill(url: "https://shop.example/bike")
        XCTAssertEqual(draft.description, "A lovely bike")
        XCTAssertEqual(draft.price, 42.5)
        XCTAssertEqual(draft.imageURL, "https://img/x.png")
        XCTAssertEqual(draft.link, "https://shop.example/bike")
    }

    func testPrefillFailureLeavesUsableLinkOnlyDraft() async {
        let vm = MyListViewModel(client: client { _ in (500, #"{"error":"upstream"}"#) }, userID: 1)
        let draft = await vm.prefill(url: "https://shop.example/bike")
        XCTAssertEqual(draft.link, "https://shop.example/bike")
        XCTAssertNil(draft.description)
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
