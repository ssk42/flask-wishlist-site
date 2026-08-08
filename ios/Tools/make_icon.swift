// Generates the Wishlist app icon (1024×1024) from code, so the asset is
// reproducible and tweakable in review.
//
//   xcrun --sdk macosx swiftc ios/Tools/make_icon.swift -o /tmp/make_icon
//   /tmp/make_icon ios/Wishlist/Assets.xcassets/AppIcon.appiconset/AppIcon.png
//
// Design: cream gift box with a gold ribbon on a cranberry radial ground —
// the same palette as the app's "warm editorial" theme (see Theme.swift).

import AppKit

let S = 1024
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: S, pixelsHigh: S,
                           bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true,
                           isPlanar: false, colorSpaceName: .deviceRGB,
                           bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
let gctx = NSGraphicsContext(bitmapImageRep: rep)!
NSGraphicsContext.current = gctx
let ctx = gctx.cgContext

func rgb(_ r: Int, _ g: Int, _ b: Int) -> CGColor {
    CGColor(red: CGFloat(r)/255, green: CGFloat(g)/255, blue: CGFloat(b)/255, alpha: 1)
}
let cranberry     = rgb(0xA5, 0x32, 0x4F)
let cranberryDeep = rgb(0x74, 0x22, 0x39)
let cranberryLift = rgb(0xBE, 0x3E, 0x5E)
let cream         = rgb(0xFB, 0xF6, 0xEF)
let creamShade    = rgb(0xEC, 0xDF, 0xCE)
let gold          = rgb(0xD8, 0xAD, 0x5A)
let goldDeep      = rgb(0xB9, 0x8B, 0x38)

// Background — radial lift so the ground isn't a flat fill.
let space = CGColorSpaceCreateDeviceRGB()
let bg = CGGradient(colorsSpace: space,
                    colors: [cranberryLift, cranberry, cranberryDeep] as CFArray,
                    locations: [0, 0.55, 1])!
ctx.drawRadialGradient(bg,
    startCenter: CGPoint(x: 512, y: 620), startRadius: 0,
    endCenter: CGPoint(x: 512, y: 512), endRadius: 760,
    options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])

func roundedRect(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ r: CGFloat) -> CGPath {
    CGPath(roundedRect: CGRect(x: x, y: y, width: w, height: h),
           cornerWidth: r, cornerHeight: r, transform: nil)
}

// The subject fills more of the canvas than naive centering would, because it
// has to read at ~40pt on the home screen.
let bodyX: CGFloat = 286, bodyY: CGFloat = 252, bodyW: CGFloat = 452, bodyH: CGFloat = 330
let lidX: CGFloat = 256,  lidY: CGFloat = 566,  lidW: CGFloat = 512, lidH: CGFloat = 110
let ribbonW: CGFloat = 88
let cx: CGFloat = 512

// Drop shadow under the whole gift.
ctx.saveGState()
ctx.setShadow(offset: CGSize(width: 0, height: -24), blur: 58, color: rgb(0x3a, 0x10, 0x1c))
ctx.addPath(roundedRect(bodyX, bodyY, bodyW, bodyH, 46))
ctx.setFillColor(cream)
ctx.fillPath()
ctx.restoreGState()

// Box body, with a shade band at the base for depth.
ctx.addPath(roundedRect(bodyX, bodyY, bodyW, bodyH, 46))
ctx.setFillColor(cream)
ctx.fillPath()
ctx.addPath(roundedRect(bodyX, bodyY, bodyW, 76, 46))
ctx.setFillColor(creamShade)
ctx.fillPath()

// Lid.
ctx.addPath(roundedRect(lidX, lidY, lidW, lidH, 34))
ctx.setFillColor(cream)
ctx.fillPath()

// Ribbons.
ctx.addPath(roundedRect(cx - ribbonW/2, bodyY, ribbonW, bodyH, 6))
ctx.setFillColor(gold)
ctx.fillPath()
ctx.addPath(roundedRect(lidX, lidY + 20, lidW, 74, 8))
ctx.setFillColor(gold)
ctx.fillPath()

// Bow — fat rotated ellipses. Thin bezier loops collapse into antennae at
// icon size, so the loops are deliberately round and heavy.
let bowBase: CGFloat = lidY + lidH - 6
func bowLoop(mirrored: Bool) {
    let dir: CGFloat = mirrored ? -1 : 1
    var t = CGAffineTransform(translationX: cx + dir * 104, y: bowBase + 74)
    t = t.rotated(by: dir * 0.42)
    let loop = CGPath(ellipseIn: CGRect(x: -86, y: -58, width: 172, height: 116), transform: &t)
    ctx.addPath(loop)
    ctx.setFillColor(gold)
    ctx.fillPath()
    ctx.addPath(loop)
    ctx.setStrokeColor(goldDeep)
    ctx.setLineWidth(7)
    ctx.strokePath()
}
bowLoop(mirrored: false)
bowLoop(mirrored: true)
// Knot last, so it sits over both loops.
ctx.addPath(roundedRect(cx - 52, bowBase - 26, 104, 78, 24))
ctx.setFillColor(goldDeep)
ctx.fillPath()

NSGraphicsContext.restoreGraphicsState()

let out = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "AppIcon.png"
let png = rep.representation(using: .png, properties: [:])!
try! png.write(to: URL(fileURLWithPath: out))
print("wrote \(out)")
