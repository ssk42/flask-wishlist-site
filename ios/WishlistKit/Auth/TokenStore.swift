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
public final class KeychainTokenStore: TokenStoring, @unchecked Sendable {
    private let account = "api-token"
    private let service = "com.reitz.wishlist"
    private let accessGroup: String?

    public init(accessGroup: String? = "com.reitz.wishlist.shared") {
        self.accessGroup = accessGroup
    }

    private func baseQuery() -> [String: Any] {
        var q: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: account,
            kSecAttrService as String: service,
        ]
        if let accessGroup { q[kSecAttrAccessGroup as String] = accessGroup }
        return q
    }

    public func read() -> String? {
        var q = baseQuery()
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var out: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess,
              let data = out as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    public func save(_ token: String) {
        clear()
        var q = baseQuery()
        q[kSecValueData as String] = Data(token.utf8)
        q[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        SecItemAdd(q as CFDictionary, nil)
    }

    public func clear() {
        SecItemDelete(baseQuery() as CFDictionary)
    }
}
