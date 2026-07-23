import Foundation

public enum APIError: Error, Equatable, Sendable {
    case unauthorized
    case conflict(code: String)
    case validation([String])
    case http(status: Int, code: String?)
    case transport(String)
    case decoding(String)

    public static func == (lhs: APIError, rhs: APIError) -> Bool {
        String(describing: lhs) == String(describing: rhs)
    }
}
