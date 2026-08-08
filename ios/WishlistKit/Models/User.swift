import Foundation

public struct User: Codable, Identifiable, Sendable, Hashable {
    public let id: Int
    public let name: String
    public let email: String
    public let itemCount: Int?

    enum CodingKeys: String, CodingKey {
        case id, name, email
        case itemCount = "item_count"
    }
}
