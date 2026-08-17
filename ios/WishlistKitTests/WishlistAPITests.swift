import XCTest
@testable import WishlistKit

final class WishlistAPITests: XCTestCase {
    func testProductionBaseURLIsHTTPS() {
        // Plain HTTP would put the family code on the wire and require an ATS
        // exception for the real host.
        XCTAssertEqual(WishlistAPI.productionBaseURL.scheme, "https")
        XCTAssertEqual(WishlistAPI.productionBaseURL.host, "gifts.stevereitz.dev")
    }

    func testLocalBaseURLAvoidsAirPlayPort() {
        XCTAssertEqual(WishlistAPI.localBaseURL.port, 8000,
                       "5000 is taken by macOS AirPlay Receiver")
    }

    func testDefaultFallsBackToProductionWhenPlistKeyAbsent() {
        // @spec IOS-NET-008
        // The test bundle has no WLAPIBaseURL, so this exercises the fallback.
        XCTAssertNil(Bundle.main.object(forInfoDictionaryKey: "WLAPIBaseURL"))
        XCTAssertEqual(WishlistAPI.defaultBaseURL, WishlistAPI.productionBaseURL)
    }

    func testSharedKeychainGroupMatchesEntitlements() {
        // Must equal the keychain-access-groups value in both targets'
        // entitlements, or the Share Extension can't read the app's token.
        XCTAssertEqual(WishlistAPI.sharedKeychainGroup, "com.reitz.wishlist.shared")
    }
}
