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
///
/// `ClaimItemIntent` has NO phrase here, and that is load-bearing rather than an
/// oversight. Interpolating its `ItemEntity` parameter — "Claim \(\.$target) in
/// \(.applicationName)" — compiles and looks correct, but breaks the build's
/// Siri Speech Understanding step:
///
///     Training 'Claim ${ItemEntity} in ${+applicationName}' for en
///     warning: unresolved variable(s) found: ItemEntity
///     Error: ... (utsKit.ResolutionError error 0.)
///     error: Could not archive SSU artifacts.
///
/// `appintentsnltrainingprocessor` needs a concrete value set at BUILD time to
/// train a phrase variable, and `WishlistItemQuery` is an `EntityStringQuery`
/// over per-user, networked, unbounded data — there is no such set. Because all
/// phrases share one corpus, that one phrase stops the whole app's nlu artifacts
/// from archiving, silently taking add/clipboard/my-claims down with it. The
/// build still reports BUILD SUCCEEDED.
///
/// Claiming by voice still works — via entity resolution, the Shortcuts app, and
/// on-screen "claim this". Only the standalone spoken phrase is gone.
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
        AppShortcut(
            intent: MyClaimsIntent(),
            phrases: [
                "What have I claimed in \(.applicationName)",
                "My \(.applicationName) claims",
            ],
            shortTitle: "My Claims",
            systemImageName: "checkmark.circle"
        )
    }
}
