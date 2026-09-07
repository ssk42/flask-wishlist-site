import Foundation

/// Case- and diacritic-insensitive substring matching for client-side search.
/// One home so every list filters the same way.
enum TextSearch {
    static func matches(_ text: String, query: String) -> Bool {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return true }
        return text.range(of: q, options: [.caseInsensitive, .diacriticInsensitive]) != nil
    }
}

/// Extracts integer ids from deep links: "/items/42" via `itemID(from:)`,
/// "/events/7" via `eventID(from:)`.
/// Centralizes the parse both push deep links (RootTabView) and in-app
/// notification taps (ActivityView) rely on, so the two can never drift.
/// @spec IOS-ACT-011, IOS-EVT-013
public enum ItemLink {
    public static func itemID(from link: String) -> Int? {
        let pattern = #"/items/(\d+)"#
        guard let range = link.range(of: pattern, options: .regularExpression) else { return nil }
        return Int(link[range].split(separator: "/").last ?? "")
    }

    /// Extracts the integer event id from an "/events/7"-shaped link.
    /// Lives next to `itemID(from:)` so push routing (`RootTabView.route`)
    /// and in-app taps (`ActivityView.openDetail`) share one parser and can
    /// never drift.
    /// @spec IOS-EVT-013
    public static func eventID(from link: String) -> Int? {
        let pattern = #"/events/(\d+)"#
        guard let range = link.range(of: pattern, options: .regularExpression) else { return nil }
        return Int(link[range].split(separator: "/").last ?? "")
    }
}
