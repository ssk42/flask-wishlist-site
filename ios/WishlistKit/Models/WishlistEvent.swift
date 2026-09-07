import Foundation

/// A family occasion from `GET /api/v1/events`. The server sends `date` as a
/// `"YYYY-MM-DD"` string (never epoch/datetime) and `item_count` excluding
/// archived items; `reminder_sent` is never exposed.
public struct WishlistEvent: Decodable, Identifiable, Sendable, Hashable {
    public struct Creator: Codable, Sendable, Hashable {
        public let id: Int
        public let name: String
    }

    public let id: Int
    public let name: String
    public let date: Date
    public let createdBy: Creator
    public let itemCount: Int
    /// Only present on embedded detail payloads; the list/detail endpoints
    /// carry items alongside the event, not inside it.
    public let items: [Item]?

    enum CodingKeys: String, CodingKey {
        case id, name, date, items
        case createdBy = "created_by"
        case itemCount = "item_count"
    }

    static let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter
    }()

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(Int.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        let day = try container.decode(String.self, forKey: .date)
        guard let parsed = Self.dayFormatter.date(from: day) else {
            throw DecodingError.dataCorruptedError(
                forKey: .date, in: container,
                debugDescription: "expected YYYY-MM-DD date string")
        }
        date = parsed
        createdBy = try container.decode(Creator.self, forKey: .createdBy)
        itemCount = try container.decode(Int.self, forKey: .itemCount)
        items = try container.decodeIfPresent([Item].self, forKey: .items)
    }

    /// True when the event's calendar day is today or later. Compares
    /// start-of-days so a later time today still counts as upcoming.
    /// @spec IOS-EVT-005
    public var isUpcoming: Bool {
        let calendar = Calendar.current
        return calendar.startOfDay(for: date) >= calendar.startOfDay(for: Date())
    }

    /// Day string for write payloads (`POST`/`PATCH` send `"YYYY-MM-DD"`).
    /// @spec IOS-EVT-006
    public var dayString: String { Self.dayFormatter.string(from: date) }
}
