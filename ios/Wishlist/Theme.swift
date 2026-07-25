import SwiftUI
import UIKit

// MARK: - Palette
//
// "Warm editorial": a cream canvas, a refined cranberry accent, and a muted
// gold highlight — a family wishlist should feel handwritten and warm, not
// like a default-gray form. Colors adapt to light/dark.

extension UIColor {
    fileprivate convenience init(rgb: UInt) {
        self.init(red: CGFloat((rgb >> 16) & 0xFF) / 255,
                  green: CGFloat((rgb >> 8) & 0xFF) / 255,
                  blue: CGFloat(rgb & 0xFF) / 255,
                  alpha: 1)
    }
    fileprivate static func wl(_ light: UInt, _ dark: UInt) -> UIColor {
        UIColor { $0.userInterfaceStyle == .dark ? UIColor(rgb: dark) : UIColor(rgb: light) }
    }

    // UIKit needs these for the navigation/tab bar appearance below.
    static let wlBgUI      = UIColor.wl(0xFBF6EF, 0x16120E)
    static let wlInkUI     = UIColor.wl(0x2A2320, 0xF3ECE3)
    static let wlAccentUI  = UIColor.wl(0xA5324F, 0xE5738D)
    static let wlSecondaryUI = UIColor.wl(0x8B7F74, 0xAA9E91)
}

extension Color {
    static let wlBg        = Color(uiColor: .wlBgUI)
    static let wlSurface   = Color(uiColor: .wl(0xFFFFFF, 0x231D18))
    static let wlAccent    = Color(uiColor: .wlAccentUI)
    static let wlAccentSoft = Color(uiColor: .wl(0xF4E3E6, 0x3A2028))
    static let wlGold      = Color(uiColor: .wl(0xB0872F, 0xD9AE5A))
    static let wlInk       = Color(uiColor: .wlInkUI)
    static let wlSecondary = Color(uiColor: .wlSecondaryUI)
    static let wlHairline  = Color(uiColor: .wl(0xEBE1D4, 0x342A22))
    static let wlGreen     = Color(uiColor: .wl(0x3F7A54, 0x76C08C))
}

// MARK: - Type
//
// New York (the system serif) as the display face — characterful and warm,
// and built in, so no bundled font files. Body stays on SF for legibility.

extension Font {
    static func wlDisplay(_ size: CGFloat, _ weight: Font.Weight = .bold) -> Font {
        .system(size: size, weight: weight, design: .serif)
    }
    static var wlTitle: Font { .system(.title2, design: .serif).weight(.semibold) }
}

// MARK: - Screen heading
//
// SwiftUI renders navigation titles in SF, which reads as "default app" beside
// the serif wordmark. Restyling them means UIKit appearance proxies, which are
// fragile (dynamic colors get snapshotted, and proxy changes race bar creation
// — both produced a blank title here). Rendering the heading as ordinary
// content is fully controllable and, for an editorial layout, better anyway:
// the title scrolls with the page like a magazine masthead.

struct WLScreenTitle: View {
    let text: String
    var accessory: AnyView?

    init(_ text: String) {
        self.text = text
        self.accessory = nil
    }

    init<A: View>(_ text: String, @ViewBuilder accessory: () -> A) {
        self.text = text
        self.accessory = AnyView(accessory())
    }

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(text)
                .font(.wlDisplay(34))
                .foregroundStyle(Color.wlInk)
            Spacer()
            if let accessory { accessory }
        }
        .padding(.horizontal, 18)
        .padding(.top, 4)
        .padding(.bottom, 10)
    }
}

// MARK: - Press feedback
//
// Cards are the primary tap target and default `.plain` gives no feedback at
// all, which makes the app feel inert. A slight scale + dim on press is enough.

struct WLCardButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
            .opacity(configuration.isPressed ? 0.88 : 1)
            .animation(.easeOut(duration: 0.12), value: configuration.isPressed)
    }
}

// MARK: - Reusable surface

struct WLCard: ViewModifier {
    var padding: CGFloat = 16
    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(Color.wlSurface, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .strokeBorder(Color.wlHairline, lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.05), radius: 10, x: 0, y: 4)
    }
}

extension View {
    func wlCard(padding: CGFloat = 16) -> some View { modifier(WLCard(padding: padding)) }
}

// MARK: - Monogram avatar

struct Monogram: View {
    let name: String
    var size: CGFloat = 44

    private var initials: String {
        let parts = name.split(separator: " ")
        let letters = parts.prefix(2).compactMap { $0.first }
        return String(letters).uppercased()
    }

    var body: some View {
        Text(initials.isEmpty ? "?" : initials)
            .font(.wlDisplay(size * 0.38, .semibold))
            .foregroundStyle(Color.wlAccent)
            .frame(width: size, height: size)
            .background(Color.wlAccentSoft, in: Circle())
    }
}

// MARK: - Priority dot

struct PriorityDot: View {
    let priority: String?
    private var color: Color {
        switch priority {
        case "High": .wlAccent
        case "Medium": .wlGold
        default: .wlSecondary.opacity(0.5)
        }
    }
    var body: some View {
        Circle().fill(color).frame(width: 8, height: 8)
    }
}

// MARK: - Status pill

struct StatusPill: View {
    let status: String
    private var tint: Color { status == "Purchased" ? .wlGreen : .wlGold }
    var body: some View {
        Text(status.uppercased())
            .font(.system(size: 10, weight: .bold))
            .tracking(0.6)
            .foregroundStyle(tint)
            .padding(.horizontal, 8).padding(.vertical, 3)
            .background(tint.opacity(0.14), in: Capsule())
    }
}
