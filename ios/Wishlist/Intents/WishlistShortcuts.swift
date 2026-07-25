import AppIntents

/// Phrases Siri recognises without the user configuring anything. Every phrase
/// must contain `\(.applicationName)` — App Intents requires it, and it is what
/// disambiguates this app from other list apps.
///
/// `itemName` is NOT interpolated into these phrases: the metadata compiler
/// rejects `\(.$param)` interpolation for any parameter that isn't an
/// `AppEntity`/`AppEnum` ("'AppEntity' and 'AppEnum' are the only allowed
/// types for 'itemName'"), and `itemName` is deliberately free-text `String`,
/// not an entity. Siri still gets the spoken item name — the parameter has
/// `requestValueDialog`, so after the trigger phrase Siri asks "What should I
/// add?" and captures the reply.
struct WishlistShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: AddWishlistItemIntent(),
            phrases: [
                "Add an item to \(.applicationName)",
                "Add to my \(.applicationName)",
                "Put something on my \(.applicationName)",
            ],
            shortTitle: "Add to Wishlist",
            systemImageName: "gift"
        )
        AppShortcut(
            intent: AddLinkFromClipboardIntent(),
            phrases: [
                "Add my clipboard to \(.applicationName)",
                "Add this link to \(.applicationName)",
            ],
            shortTitle: "Add Clipboard Link",
            systemImageName: "link"
        )
    }
}
