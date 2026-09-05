import XCTest
@testable import WishlistKit

@MainActor
final class ClaimsViewModelTests: XCTestCase {
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

    func testUnclaimRemovesItem() async {
        // @spec IOS-GIFT-007
        let vm = ClaimsViewModel(client: client { req in
            if req.url!.path.hasSuffix("/unclaim") {
                return (200, #"{"item":{"id":5,"description":"Book","user_id":2,"status":"Available"}}"#)
            }
            return (200, #"{"items":[{"id":5,"description":"Book","user_id":2,"status":"Claimed"}]}"#)
        })
        await vm.load()
        XCTAssertEqual(vm.items.count, 1)
        await vm.unclaim(vm.items[0])
        XCTAssertTrue(vm.items.isEmpty)
        XCTAssertNil(vm.error)
    }

    func testUnclaimConflictSetsSharedCopy() async {
        // @spec IOS-GIFT-004, IOS-GIFT-007
        let vm = ClaimsViewModel(client: client { req in
            if req.url!.path.hasSuffix("/unclaim") { return (409, #"{"error":"claimed_by_other"}"#) }
            return (200, #"{"items":[{"id":5,"description":"Book","user_id":2,"status":"Claimed"}]}"#)
        })
        await vm.load()
        await vm.unclaim(vm.items[0])
        XCTAssertEqual(vm.error, "This item is claimed by someone else.")
        XCTAssertEqual(vm.items.count, 1)
    }

    func testPurchaseConflictSetsSharedCopy() async {
        // @spec IOS-GIFT-004, IOS-GIFT-007
        let vm = ClaimsViewModel(client: client { req in
            if req.url!.path.hasSuffix("/purchase") { return (409, #"{"error":"already_purchased"}"#) }
            return (200, #"{"items":[{"id":5,"description":"Book","user_id":2,"status":"Claimed"}]}"#)
        })
        await vm.load()
        await vm.purchase(vm.items[0])
        XCTAssertEqual(vm.error, "This item is already purchased.")
        XCTAssertEqual(vm.items.count, 1)
    }

    func testQueryFiltersClaimsByDescriptionAndCategory() async {
        // @spec IOS-GIFT-013
        let vm = ClaimsViewModel(client: client { _ in
            (200, #"{"items":[{"id":1,"description":"Stand mixer","category":"Kitchen","status":"Claimed","user_id":2},{"id":2,"description":"Novel","category":"Books","status":"Purchased","user_id":3}]}"#)
        })
        await vm.load()
        vm.query = "kitchen"
        XCTAssertEqual(vm.filteredItems.map(\.id), [1])
        vm.query = ""
        XCTAssertEqual(vm.filteredItems.map(\.id), [1, 2])
        vm.query = "nope"
        XCTAssertTrue(vm.filteredItems.isEmpty)
        XCTAssertEqual(vm.items.count, 2)
    }

    func testStatusFilterAndsWithQuery() async {
        // @spec IOS-GIFT-013
        let vm = ClaimsViewModel(client: client { _ in
            (200, #"{"items":[{"id":1,"description":"Stand mixer","category":"Kitchen","status":"Claimed","user_id":2},{"id":2,"description":"Novel","category":"Books","status":"Purchased","user_id":3}]}"#)
        })
        await vm.load()
        vm.selectedStatus = "Claimed"
        XCTAssertEqual(vm.filteredItems.map(\.id), [1])
        vm.query = "novel"
        XCTAssertTrue(vm.filteredItems.isEmpty)
        vm.query = ""
        vm.selectedStatus = nil
        XCTAssertEqual(vm.filteredItems.map(\.id), [1, 2])
    }

}
