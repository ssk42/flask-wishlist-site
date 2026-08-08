import Foundation
import Observation

/// Drives the Share Extension: prefill an item from a shared URL, let the user
/// adjust it, then post it. Runs in the extension process, so it authenticates
/// with the token the app stored in the shared Keychain group.
@MainActor @Observable
public final class ShareItemViewModel {
    public var draft = ItemDraft()
    public private(set) var error: String?
    public private(set) var needsLogin = false
    public var isLoading = false

    private let client: APIClient

    public init(client: APIClient) { self.client = client }

    /// Fetch title/price/image for the shared URL. Best-effort: a failed lookup
    /// still leaves a usable form (the link is filled, user types the rest).
    public func prefill(urlString: String) async {
        isLoading = true
        error = nil
        draft.link = urlString
        do {
            let fetched = try await client.fetchMetadata(url: urlString)
            if let description = fetched.description, !description.isEmpty {
                draft.description = description
            }
            draft.price = fetched.price
            draft.imageURL = fetched.imageURL
            draft.link = urlString      // always the shared URL, not the server's echo
        } catch APIError.unauthorized {
            needsLogin = true
            error = "Open the Wishlist app and log in first."
        } catch {
            // Metadata is a convenience, not a requirement — stay silent.
        }
        isLoading = false
    }

    public var canSubmit: Bool {
        !(draft.description ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    @discardableResult
    public func submit() async -> Bool {
        guard canSubmit else {
            error = "Add a short description."
            return false
        }
        error = nil
        do {
            _ = try await client.createItem(draft)
            return true
        } catch APIError.unauthorized {
            needsLogin = true
            error = "Open the Wishlist app and log in first."
            return false
        } catch APIError.validation(let messages) {
            error = messages.first ?? "Please check the fields."
            return false
        } catch {
            // `self.` is required: a bare `catch` binds `error` to the thrown value.
            self.error = "Couldn't save. Try again."
            return false
        }
    }
}
