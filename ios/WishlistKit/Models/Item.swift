import Foundation

public struct ItemActor: Codable, Sendable, Hashable {
    public let id: Int
    public let name: String
}

public struct Item: Codable, Identifiable, Sendable, Hashable {
    public let id: Int
    public let description: String
    public let link: String?
    public let price: Double?
    public let category: String?
    public let imageURL: String?
    public let priority: String?
    public let eventID: Int?
    public let size: String?
    public let color: String?
    public let quantity: Int?
    public let userID: Int
    public let createdAt: String?
    public let updatedAt: String?
    /// nil for the viewer's OWN items (server omits it — surprise protection).
    public let status: String?
    /// nil for the viewer's own items, or when unclaimed.
    public let lastUpdatedBy: ItemActor?

    enum CodingKeys: String, CodingKey {
        case id, description, link, price, category, priority, size, color, quantity, status
        case imageURL = "image_url"
        case eventID = "event_id"
        case userID = "user_id"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case lastUpdatedBy = "last_updated_by"
    }

    /// True when this item belongs to the viewing user (status hidden by the server).
    public var isOwn: Bool { status == nil }
}
