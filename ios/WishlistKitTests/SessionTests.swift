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
        // @spec IOS-AUTH-002
        let store = InMemoryTokenStore()
        let session = makeSession(loginStatus: 200, tokenStore: store)
        let ok = await session.logIn(email: "a@x.com", familyCode: "secret")
        XCTAssertTrue(ok)
        XCTAssertEqual(store.read(), "tok")
        if case .loggedIn(let u) = session.state { XCTAssertEqual(u.name, "Alex") } else { XCTFail("expected loggedIn") }
    }

    func testFailedLoginStaysLoggedOut() async {
        // @spec IOS-AUTH-001, IOS-AUTH-002
        let session = makeSession(loginStatus: 401)
        let ok = await session.logIn(email: "x", familyCode: "y")
        XCTAssertFalse(ok)
        if case .loggedOut = session.state {} else { XCTFail("expected loggedOut") }
    }

    func testLogOutClearsToken() async {
        // @spec IOS-AUTH-003
        let store = InMemoryTokenStore(); store.save("tok")
        let session = makeSession(loginStatus: 200, tokenStore: store)
        _ = await session.logIn(email: "a@x.com", familyCode: "secret")
        await session.logOut()
        XCTAssertNil(store.read())
        if case .loggedOut = session.state {} else { XCTFail("expected loggedOut") }
    }

    // MARK: bootstrap (session restore from a stored token)

    private func makeBootstrapSession(status: Int) -> (Session, InMemoryTokenStore) {
        let store = InMemoryTokenStore()
        StubURLProtocol.handler = { req in
            let body = status == 200
                ? #"{"user":{"id":1,"name":"Alex","email":"a@x.com"}}"#
                : #"{"error":"unauthorized"}"#
            return (HTTPURLResponse(url: req.url!, statusCode: status,
                                    httpVersion: nil, headerFields: nil)!,
                    Data(body.utf8))
        }
        let client = APIClient(baseURL: URL(string: "http://test.local")!,
                               session: StubURLProtocol.session(),
                               tokenProvider: { store.read() })
        return (Session(client: client, tokenStore: store), store)
    }

    func testBootstrapWithNoTokenStaysLoggedOut() async {
        let (session, _) = makeBootstrapSession(status: 200)
        await session.bootstrap()
        if case .loggedOut = session.state {} else { XCTFail("expected loggedOut") }
    }

    func testBootstrapRestoresLoggedInFromStoredToken() async {
        let (session, store) = makeBootstrapSession(status: 200)
        store.save("tok")
        await session.bootstrap()
        if case .loggedIn(let u) = session.state {
            XCTAssertEqual(u.id, 1)
            XCTAssertEqual(u.name, "Alex")
        } else { XCTFail("expected loggedIn") }
    }

    func testBootstrapClearsTokenOn401() async {
        let (session, store) = makeBootstrapSession(status: 401)
        store.save("tok")
        await session.bootstrap()
        XCTAssertNil(store.read())
        if case .loggedOut = session.state {} else { XCTFail("expected loggedOut") }
    }
}
