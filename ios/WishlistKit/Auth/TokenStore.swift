import Foundation
import Security

public protocol TokenStoring: Sendable {
    func read() -> String?
    func save(_ token: String)
    func clear()
}

public final class InMemoryTokenStore: TokenStoring, @unchecked Sendable {
    private let lock = NSLock()
    private var value: String?
    public init() {}
    public func read() -> String? { lock.withLock { value } }
    public func save(_ token: String) { lock.withLock { value = token } }
    public func clear() { lock.withLock { value = nil } }
}

/// Stores the API token in the shared Keychain access group so the app and the
/// Share Extension authenticate with the same credential.
///
/// An in-memory cache fronts the Keychain: within a process, reads always see
/// the last saved token even if every Keychain write fails (e.g. unsigned
/// simulator builds without the keychain entitlement). The Keychain remains
/// the persistent layer for relaunches and the Share Extension.
/// @spec IOS-AUTH-004
public final class KeychainTokenStore: TokenStoring, @unchecked Sendable {
    private let account = "api-token"
    private let service = "com.reitz.wishlist"
    private let accessGroup: String?
    private let lock = NSLock()
    private var cached: String?

    public init(accessGroup: String? = "com.reitz.wishlist.shared") {
        self.accessGroup = accessGroup
    }

    /// Try the shared access group first — it works on signed device/TestFlight
    /// builds and lets the Share Extension read the same token. Fall back to the
    /// app's default keychain (no group), which is what works on unsigned
    /// simulator builds that lack the keychain-access-groups entitlement.
    private var groupsToTry: [String?] {
        if let accessGroup { return [accessGroup, nil] }
        return [nil]
    }

    private func query(group: String?) -> [String: Any] {
        var q: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: account,
            kSecAttrService as String: service,
        ]
        if let group { q[kSecAttrAccessGroup as String] = group }
        return q
    }

    public func read() -> String? {
        if let token = lock.withLock({ cached }) { return token }
        for group in groupsToTry {
            var q = query(group: group)
            q[kSecReturnData as String] = true
            q[kSecMatchLimit as String] = kSecMatchLimitOne
            var out: CFTypeRef?
            if SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess,
               let data = out as? Data, let token = String(data: data, encoding: .utf8) {
                lock.withLock { cached = token }
                return token
            }
        }
        return nil
    }

    public func save(_ token: String) {
        // @spec IOS-AUTH-005
        lock.withLock { cached = token }
        clearKeychain()
        for group in groupsToTry {
            var q = query(group: group)
            q[kSecValueData as String] = Data(token.utf8)
            q[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
            if SecItemAdd(q as CFDictionary, nil) == errSecSuccess { return }
        }
    }

    public func clear() {
        lock.withLock { cached = nil }
        clearKeychain()
    }

    private func clearKeychain() {
        for group in groupsToTry {
            SecItemDelete(query(group: group) as CFDictionary)
        }
    }
}
