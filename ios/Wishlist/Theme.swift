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
}

extension Color {
    static let wlBg        = Color(uiColor: .wl(0xFBF6EF, 0x16120E))
    static let wlSurface   = Color(uiColor: .wl(0xFFFFFF, 0x231D18))
    static let wlAccent    = Color(uiColor: .wl(0xA5324F, 0xE5738D))
    static let wlAccentSoft = Color(uiColor: .wl(0xF4E3E6, 0x3A2028))
    static let wlGold      = Color(uiColor: .wl(0xB0872F, 0xD9AE5A))
    static let wlInk       = Color(uiColor: .wl(0x2A2320, 0xF3ECE3))
    static let wlSecondary = Color(uiColor: .wl(0x8B7F74, 0xAA9E91))
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
