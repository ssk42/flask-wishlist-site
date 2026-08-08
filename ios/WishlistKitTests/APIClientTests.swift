import XCTest
@testable import WishlistKit

final class APIClientTests: XCTestCase {
    private let base = URL(string: "http://test.local")!

    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    private func makeClient(token: String? = "tok") -> APIClient {
        APIClient(baseURL: base, session: StubURLProtocol.session(), tokenProvider: { token })
    }

    private func respond(_ status: Int, _ body: String) {
        StubURLProtocol.handler = { req in
            (HTTPURLResponse(url: req.url!, statusCode: status, httpVersion: nil, headerFields: nil)!,
             Data(body.utf8))
        }
    }

    func testLoginSendsCredentialsAndDecodesToken() async throws {
        var captured: URLRequest?
        StubURLProtocol.handler = { req in
            captured = req
            let body = #"{"token":"abc123","user":{"id":1,"name":"Alex","email":"a@x.com"}}"#
            return (HTTPURLResponse(url: req.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, Data(body.utf8))
        }
        let client = makeClient(token: nil)
        let result = try await client.login(email: "a@x.com", familyCode: "secret")
        XCTAssertEqual(result.token, "abc123")
        XCTAssertEqual(result.user.name, "Alex")
        XCTAssertEqual(captured?.url?.path, "/api/v1/auth/login")
        XCTAssertEqual(captured?.httpMethod, "POST")
    }

    func testAttachesBearerHeaderWhenTokenPresent() async throws {
        var captured: URLRequest?
        StubURLProtocol.handler = { req in
            captured = req
            return (HTTPURLResponse(url: req.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, Data("{}".utf8))
        }
        _ = try? await makeClient(token: "tok").logout()
        XCTAssertEqual(captured?.value(forHTTPHeaderField: "Authorization"), "Bearer tok")
    }

    func testMaps401ToUnauthorized() async {
        respond(401, #"{"error":"unauthorized"}"#)
        do { _ = try await makeClient().login(email: "x", familyCode: "y"); XCTFail("expected throw") }
        catch let APIError.unauthorized { /* ok */ }
        catch { XCTFail("wrong error: \(error)") }
    }

    // testMaps409ToConflictWithCode is intentionally omitted from this task:
    // it exercises `client.claim(itemID:)`, which wasn't implemented until
    // Task 6. It landed there as `testClaimConflictThrows` in
    // APIClientWriteTests.swift.
}
