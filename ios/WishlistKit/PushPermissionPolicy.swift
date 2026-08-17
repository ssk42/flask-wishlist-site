import Foundation
import UserNotifications

/// What `PushManager` should do for a given OS notification-authorization status.
/// The OS status is the once-per-install source of truth: `.notDetermined` is the
/// only state from which a system prompt can appear, and after the user answers
/// (granted/denied/provisional) the OS never re-prompts that install.
public enum PushPermissionAction: Sendable, Equatable {
    /// Never asked before — request authorization, then register if granted.
    case requestAndRegister
    /// Already granted — keep the APNs token current without prompting.
    case register
    /// Denied — do not prompt again, do not register.
    case skip
}

/// Pure decision mapping for push-permission handling (testable without a
/// notification center).
public enum PushPermissionPolicy {
    /// @spec IOS-ACT-009
    public static func action(for status: UNAuthorizationStatus) -> PushPermissionAction {
        switch status {
        case .notDetermined: return .requestAndRegister
        case .authorized, .provisional, .ephemeral: return .register
        case .denied: return .skip
        @unknown default: return .skip
        }
    }
}