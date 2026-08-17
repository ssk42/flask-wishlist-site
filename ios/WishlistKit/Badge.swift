import Foundation

/// App-icon badge policy: the badge shows the unread notification count, capped
/// at 99 (iOS renders a bare "99+" above that — a raw number would be misleading).
public enum Badge {
    /// @spec IOS-ACT-010
    public static func value(unreadCount: Int) -> Int {
        min(max(unreadCount, 0), 99)
    }
}