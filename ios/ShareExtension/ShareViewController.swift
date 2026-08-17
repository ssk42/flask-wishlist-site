import SwiftUI
import UIKit
import UniformTypeIdentifiers
import WishlistKit

/// Hosts the SwiftUI share sheet. Authenticates with the token the main app
/// wrote to the shared Keychain group — hence no login UI here; if the token is
/// missing, the view tells the user to open the app first.
final class ShareViewController: UIViewController {
    private let tokenStore = KeychainTokenStore(accessGroup: WishlistAPI.sharedKeychainGroup)

    override func viewDidLoad() {
        super.viewDidLoad()
        Task { await present() }
    }

    private func present() async {
        guard let urlString = await sharedURL() else {
            // Nothing usable was shared; close rather than show an empty form.
            cancel()
            return
        }

        let store = tokenStore
        let client = APIClient(baseURL: WishlistAPI.defaultBaseURL,
                               tokenProvider: { store.read() })
        let vm = ShareItemViewModel(client: client)

        let root = ShareView(
            vm: vm,
            urlString: urlString,
            onFinished: { [weak self] in self?.complete() },
            onCancel: { [weak self] in self?.cancel() }
        )

        let host = UIHostingController(rootView: root)
        addChild(host)
        host.view.frame = view.bounds
        host.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(host.view)
        host.didMove(toParent: self)
    }

    /// Safari shares a `public.url`; some apps share the link as plain text.
    /// @spec IOS-SHARE-001
    private func sharedURL() async -> String? {
        let items = (extensionContext?.inputItems as? [NSExtensionItem]) ?? []
        for item in items {
            for provider in item.attachments ?? [] {
                if let url = await loadString(provider, as: UTType.url.identifier,
                                             transform: { ($0 as? URL)?.absoluteString }) {
                    return url
                }
                if let text = await loadString(provider, as: UTType.plainText.identifier,
                                               transform: { $0 as? String }),
                   let match = text.split(separator: " ").first(where: { $0.hasPrefix("http") }) {
                    return String(match)
                }
            }
        }
        return nil
    }

    /// The loaded item is not `Sendable`, so it is reduced to a String *inside*
    /// the completion handler; only that crosses the continuation.
    private func loadString(_ provider: NSItemProvider,
                            as identifier: String,
                            transform: @escaping @Sendable (NSSecureCoding?) -> String?) async -> String? {
        guard provider.hasItemConformingToTypeIdentifier(identifier) else { return nil }
        return await withCheckedContinuation { (continuation: CheckedContinuation<String?, Never>) in
            provider.loadItem(forTypeIdentifier: identifier, options: nil) { value, _ in
                continuation.resume(returning: transform(value))
            }
        }
    }

    private func complete() {
        extensionContext?.completeRequest(returningItems: nil)
    }

    private func cancel() {
        extensionContext?.cancelRequest(withError: NSError(domain: "com.reitz.wishlist.share",
                                                          code: NSUserCancelledError))
    }
}
