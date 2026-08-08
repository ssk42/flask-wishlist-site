import XCTest
@testable import WishlistKit

final class TokenStoreTests: XCTestCase {
    func testSaveReadClearRoundTrip() {
        let store = InMemoryTokenStore()
        XCTAssertNil(store.read())
        store.save("abc")
        XCTAssertEqual(store.read(), "abc")
        store.clear()
        XCTAssertNil(store.read())
    }

    func testSaveOverwrites() {
        let store = InMemoryTokenStore()
        store.save("one"); store.save("two")
        XCTAssertEqual(store.read(), "two")
    }
}
