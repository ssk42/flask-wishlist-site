import Foundation

public struct ItemDraft: Sendable {
    public var description: String?
    public var link: String?
    public var price: Double?
    public var category: String?
    public var imageURL: String?
    public var priority: String?
    public var size: String?
    public var color: String?
    public var quantity: Int?

    public init(description: String? = nil, link: String? = nil, price: Double? = nil,
                category: String? = nil, imageURL: String? = nil, priority: String? = nil,
                size: String? = nil, color: String? = nil, quantity: Int? = nil) {
        self.description = description; self.link = link; self.price = price
        self.category = category; self.imageURL = imageURL; self.priority = priority
        self.size = size; self.color = color; self.quantity = quantity
    }

    /// All fields, nils included. The single place nil-dropping happens is
    /// `APIClient.sendRaw` (`compactMapValues`), so PATCH stays a true partial
    /// update without a second filter here.
    /// @spec IOS-NET-006
    public var payload: [String: Any?] {
        [
            "description": description, "link": link, "price": price, "category": category,
            "image_url": imageURL, "priority": priority, "size": size, "color": color,
            "quantity": quantity,
        ]
    }
}
