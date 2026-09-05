import XCTest
@testable import WishlistKit

@MainActor
final class MemberItemsViewModelTests: XCTestCase {
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

    private func memberItemsClient() -> APIClient {
        client { _ in
            (200, #"{"items":[{"id":1,"description":"Stand mixer","category":"Kitchen","priority":"High","status":"Available","user_id":2},{"id":2,"description":"Novel","category":"Books","priority":"Low","status":"Claimed","user_id":2},{"id":3,"description":"Socks","user_id":2}]}"#)
        }
    }

    private func makeVM() async -> MemberItemsViewModel {
        let vm = MemberItemsViewModel(client: memberItemsClient(),
                                      member: User(id: 2, name: "Sam", email: "s@x.com", itemCount: 3))
        await vm.load()
        return vm
    }

    func testSearchFiltersByDescriptionAndCategory() async {
        // @spec IOS-GIFT-011
        let vm = await makeVM()
        vm.query = "kitchen"
        XCTAssertEqual(vm.filteredItems.map(\.id), [1])
        vm.query = "NOVEL"
        XCTAssertEqual(vm.filteredItems.map(\.id), [2])
    }

    func testEmptyQueryShowsAll() async {
        // @spec IOS-GIFT-011
        let vm = await makeVM()
        vm.query = ""
        XCTAssertEqual(vm.filteredItems.map(\.id), [1, 2, 3])
    }

    func testNoMatchShowsNoResultsWhileItemsRemain() async {
        // @spec IOS-GIFT-011
        let vm = await makeVM()
        vm.query = "nope"
        XCTAssertTrue(vm.filteredItems.isEmpty)
        XCTAssertEqual(vm.items.count, 3)
    }

    func testFiltersAndWithQuery() async {
        // @spec IOS-GIFT-012
        let vm = await makeVM()
        vm.query = "e"
        vm.selectedStatus = "Claimed"
        XCTAssertEqual(vm.filteredItems.map(\.id), [2])
        vm.query = ""
        vm.selectedStatus = "Available"
        vm.selectedPriority = "High"
        XCTAssertEqual(vm.filteredItems.map(\.id), [1])
    }

    func testUnsetFiltersConstrainNothing() async {
        // @spec IOS-GIFT-012
        let vm = await makeVM()
        XCTAssertEqual(vm.filteredItems.map(\.id), [1, 2, 3])
        vm.selectedCategory = "Kitchen"
        XCTAssertEqual(vm.filteredItems.map(\.id), [1])
        vm.selectedCategory = nil
        XCTAssertEqual(vm.filteredItems.map(\.id), [1, 2, 3])
    }

    func testNilFieldsMatchOnlyAll() async {
        // @spec IOS-GIFT-012
        let vm = await makeVM()
        vm.selectedPriority = "High"
        XCTAssertEqual(vm.filteredItems.map(\.id), [1])
        vm.selectedPriority = nil
        vm.selectedCategory = "Books"
        XCTAssertEqual(vm.filteredItems.map(\.id), [2])
    }

    func testFilterNoMatchKeepsSourceItems() async {
        // @spec IOS-GIFT-012
        let vm = await makeVM()
        vm.selectedStatus = "Purchased"
        XCTAssertTrue(vm.filteredItems.isEmpty)
        XCTAssertEqual(vm.items.count, 3)
    }
}
