import AppIntents
import Foundation

/// An item as Siri sees it.
///
/// `status` is optional and absent for the caller's own items, mirroring the
/// server's serializer. `displayRepresentation` — the text Siri speaks — must
/// never mention claim state for an own item.
public struct ItemEntity: AppEntity, Sendable {
    public let id: Int
    public let name: String
    public let ownerName: String?
    public let price: Double?
    public let status: String?
    /// The owner's user id. Deliberately not `@Property` — same reasoning as
    /// `status`: it exists so the app can navigate to the right member's item
    /// list when an "open" intent fires, not for the system to expose or speak.
    public let ownerID: Int

    public init(item: Item, ownerName: String?) {
        self.id = item.id
        self.name = item.description
        self.ownerName = ownerName
        self.price = item.price
        self.status = item.status      // nil for own items — never defaulted
        self.ownerID = item.userID
    }

    public static let typeDisplayRepresentation: TypeDisplayRepresentation = "Wishlist Item"

    public var displayRepresentation: DisplayRepresentation {
        var subtitleParts: [String] = []
        if let ownerName { subtitleParts.append(ownerName) }
        if let price {
            subtitleParts.append(price.formatted(.currency(code: "USD")))
        }
        // Claim state is spoken only for other people's items. For an own item
        // `status` is nil, so nothing to leak.
        if let status, status != "Available" { subtitleParts.append(status) }

        return DisplayRepresentation(
            title: "\(name)",
            subtitle: subtitleParts.isEmpty ? nil : "\(subtitleParts.joined(separator: " · "))"
        )
    }

    public static let defaultQuery = WishlistItemQuery()
}

/// Resolves entities by id (for "open this") and by spoken text (for search).
public struct WishlistItemQuery: EntityStringQuery {
    public init() {}

    public func entities(for identifiers: [ItemEntity.ID]) async throws -> [ItemEntity] {
        try await IntentService.shared.entities(for: identifiers)
    }

    public func entities(matching string: String) async throws -> [ItemEntity] {
        try await IntentService.shared.searchItems(matching: string)
    }
}
