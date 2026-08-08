import Foundation

public struct WishlistNotification: Codable, Identifiable, Sendable, Hashable {
    public let id: Int
    public let message: String
    public let link: String
    public let isRead: Bool
    public let createdAt: String?

    enum CodingKeys: String, CodingKey {
        case id, message, link
        case isRead = "is_read"
        case createdAt = "created_at"
    }
}
