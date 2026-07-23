import Foundation

public struct LoginResponse: Decodable, Sendable {
    public let token: String
    public let user: User
}

public actor APIClient {
    public let baseURL: URL
    private let session: URLSession
    private let tokenProvider: @Sendable () async -> String?
    private let decoder = JSONDecoder()

    public init(baseURL: URL,
                session: URLSession = .shared,
                tokenProvider: @escaping @Sendable () async -> String?) {
        self.baseURL = baseURL
        self.session = session
        self.tokenProvider = tokenProvider
    }

    // MARK: Auth
    public func login(email: String, familyCode: String) async throws -> LoginResponse {
        try await send(.post, "/api/v1/auth/login",
                       body: ["email": email, "family_code": familyCode],
                       authenticated: false)
    }

    public func logout() async throws {
        _ = try await sendRaw(.post, "/api/v1/auth/logout", body: nil, authenticated: true)
    }

    // MARK: Request machinery
    enum Method: String { case get = "GET", post = "POST", patch = "PATCH", delete = "DELETE" }

    func send<T: Decodable>(_ method: Method, _ path: String,
                            body: [String: Any?]? = nil,
                            authenticated: Bool = true) async throws -> T {
        let data = try await sendRaw(method, path, body: body, authenticated: authenticated)
        do { return try decoder.decode(T.self, from: data) }
        catch { throw APIError.decoding(String(describing: error)) }
    }

    @discardableResult
    func sendRaw(_ method: Method, _ path: String,
                 body: [String: Any?]?, authenticated: Bool) async throws -> Data {
        // NOTE: `baseURL.appendingPathComponent(path)` can percent-encode the
        // leading slash of an absolute path like "/api/v1/auth/login", which
        // breaks callers that assert on `request.url?.path`. Building the URL
        // via `URL(string:relativeTo:)` instead treats `path` as a normal
        // absolute-path URL string resolved against baseURL, which preserves
        // the path exactly and also supports query strings (needed by later
        // read endpoints) without extra encoding surprises.
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw APIError.transport("bad url")
        }
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            let clean = body.compactMapValues { $0 }
            request.httpBody = try JSONSerialization.data(withJSONObject: clean)
        }
        if authenticated, let token = await tokenProvider() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let data: Data, response: URLResponse
        do { (data, response) = try await session.data(for: request) }
        catch { throw APIError.transport(String(describing: error)) }

        guard let http = response as? HTTPURLResponse else { throw APIError.transport("no HTTP response") }
        switch http.statusCode {
        case 200...299: return data
        case 401: throw APIError.unauthorized
        case 409: throw APIError.conflict(code: Self.errorCode(data) ?? "conflict")
        case 400:
            if let errs = Self.validationErrors(data) { throw APIError.validation(errs) }
            throw APIError.http(status: 400, code: Self.errorCode(data))
        default: throw APIError.http(status: http.statusCode, code: Self.errorCode(data))
        }
    }

    private static func errorCode(_ data: Data) -> String? {
        (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["error"] as? String
    }
    private static func validationErrors(_ data: Data) -> [String]? {
        (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["errors"] as? [String]
    }
}
