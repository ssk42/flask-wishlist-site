import XCTest
@testable import WishlistKit

@MainActor
final class SessionTests: XCTestCase {
    private func makeSession(loginStatus: Int, tokenStore: TokenStoring = InMemoryTokenStore()) -> Session {
        StubURLProtocol.handler = { req in
            let body = #"{"token":"tok","user":{"id":1,"name":"Alex","email":"a@x.com"}}"#
            let payload = loginStatus == 200 ? body : #"{"error":"unknown_email"}"#
            return (HTTPURLResponse(url: req.url!, statusCode: loginStatus, httpVersion: nil, headerFields: nil)!,
                    Data(payload.utf8))
        }
        let client = APIClient(baseURL: URL(string: "http://test.local")!,
                               session: StubURLProtocol.session(),
                               tokenProvider: { tokenStore.read() })
        return Session(client: client, tokenStore: tokenStore)
    }

    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    func testSuccessfulLoginStoresTokenAndUser() async {
        let store = InMemoryTokenStore()
        let session = makeSession(loginStatus: 200, tokenStore: store)
        let ok = await session.logIn(email: "a@x.com", familyCode: "secret")
        XCTAssertTrue(ok)
        XCTAssertEqual(store.read(), "tok")
        if case .loggedIn(let u) = session.state { XCTAssertEqual(u.name, "Alex") } else { XCTFail("expected loggedIn") }
    }

    func testFailedLoginStaysLoggedOut() async {
        let session = makeSession(loginStatus: 401)
        let ok = await session.logIn(email: "x", familyCode: "y")
        XCTAssertFalse(ok)
        if case .loggedOut = session.state {} else { XCTFail("expected loggedOut") }
    }

    func testLogOutClearsToken() async {
        let store = InMemoryTokenStore(); store.save("tok")
        let session = makeSession(loginStatus: 200, tokenStore: store)
        _ = await session.logIn(email: "a@x.com", familyCode: "secret")
        await session.logOut()
        XCTAssertNil(store.read())
        if case .loggedOut = session.state {} else { XCTFail("expected loggedOut") }
    }
}
