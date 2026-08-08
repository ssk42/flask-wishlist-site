import XCTest
@testable import WishlistKit

@MainActor
final class FamilyViewModelTests: XCTestCase {
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

    func testLoadFillsUsers() async {
        let vm = FamilyViewModel(client: client { _ in
            (200, #"{"users":[{"id":1,"name":"Alex","email":"a@x.com","item_count":2}]}"#)
        })
        await vm.load()
        XCTAssertEqual(vm.users.map(\.name), ["Alex"])
        XCTAssertNil(vm.error)
    }

    func testLoadSetsErrorOnFailure() async {
        let vm = FamilyViewModel(client: client { _ in (500, #"{"error":"server_error"}"#) })
        await vm.load()
        XCTAssertTrue(vm.users.isEmpty)
        XCTAssertNotNil(vm.error)
    }

    func testClaimUpdatesItem() async {
        let vm = MemberItemsViewModel(client: client { req in
            if req.url!.path.hasSuffix("/claim") {
                return (200, #"{"item":{"id":5,"description":"Book","user_id":2,"status":"Claimed","last_updated_by":{"id":1,"name":"Alex"}}}"#)
            }
            return (200, #"{"items":[{"id":5,"description":"Book","user_id":2,"status":"Available"}]}"#)
        }, member: User(id: 2, name: "Sam", email: "s@x.com", itemCount: 1))
        await vm.load()
        XCTAssertEqual(vm.items.first?.status, "Available")
        await vm.claim(vm.items[0])
        XCTAssertEqual(vm.items[0].status, "Claimed")
    }

    func testClaimConflictSetsFriendlyError() async {
        let vm = MemberItemsViewModel(client: client { req in
            if req.url!.path.hasSuffix("/claim") { return (409, #"{"error":"own_item"}"#) }
            return (200, #"{"items":[{"id":5,"description":"Book","user_id":2,"status":"Available"}]}"#)
        }, member: User(id: 2, name: "Sam", email: "s@x.com", itemCount: 1))
        await vm.load()
        await vm.claim(vm.items[0])
        XCTAssertEqual(vm.error, "You can't claim your own item.")
        XCTAssertEqual(vm.items[0].status, "Available")
    }
}
