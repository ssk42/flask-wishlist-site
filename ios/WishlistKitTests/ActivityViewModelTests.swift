import XCTest
@testable import WishlistKit

@MainActor
final class ActivityViewModelTests: XCTestCase {
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    /// Serves notifications with a mutable read state so mark-all-read is observable.
    private final class FakeServer: @unchecked Sendable {
        var allRead = false
        var readAllCalled = false

        func respond(_ req: URLRequest) -> (Int, String) {
            if req.url!.path.hasSuffix("/read-all") {
                readAllCalled = true; allRead = true
                return (200, #"{"ok":true}"#)
            }
            let isRead = allRead ? "true" : "false"
            let unread = allRead ? 0 : 2
            return (200, """
                {"notifications":[
                  {"id":1,"message":"Mom commented","link":"/items/1","is_read":\(isRead),"created_at":null},
                  {"id":2,"message":"Price drop","link":"/items/2","is_read":\(isRead),"created_at":null}
                ],"unread_count":\(unread)}
                """)
        }
    }

    private func client(_ server: FakeServer) -> APIClient {
        StubURLProtocol.handler = { req in
            let (status, json) = server.respond(req)
            return (HTTPURLResponse(url: req.url!, statusCode: status, httpVersion: nil, headerFields: nil)!,
                    Data(json.utf8))
        }
        return APIClient(baseURL: URL(string: "http://t.local")!,
                         session: StubURLProtocol.session(),
                         tokenProvider: { "tok" })
    }

    func testLoadFillsNotificationsAndUnreadCount() async {
        // @spec IOS-ACT-001
        let vm = ActivityViewModel(client: client(FakeServer()))
        await vm.load()
        XCTAssertEqual(vm.notifications.map(\.id), [1, 2])
        XCTAssertEqual(vm.unreadCount, 2)
        XCTAssertNil(vm.error)
    }

    func testMarkAllReadPostsAndRefreshes() async {
        // @spec IOS-ACT-003
        let server = FakeServer()
        let vm = ActivityViewModel(client: client(server))
        await vm.load()
        await vm.markAllRead()
        XCTAssertTrue(server.readAllCalled)
        XCTAssertEqual(vm.unreadCount, 0)
        XCTAssertTrue(vm.notifications.allSatisfy(\.isRead))
    }
}
