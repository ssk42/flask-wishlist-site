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

/// Extracts the integer item id from a "/items/42"-shaped link.
/// Centralizes the parse both push deep links (RootTabView) and in-app
/// notification taps (ActivityView) rely on, so the two can never drift.
/// @spec IOS-ACT-011
public enum ItemLink {
    public static func itemID(from link: String) -> Int? {
        let pattern = #"/items/(\d+)"#
        guard let range = link.range(of: pattern, options: .regularExpression) else { return nil }
        return Int(link[range].split(separator: "/").last ?? "")
    }
}
