import XCTest
import UserNotifications
@testable import WishlistKit

final class PushPermissionPolicyTests: XCTestCase {
    func testNotDeterminedRequestsPermission() {
        XCTAssertEqual(PushPermissionPolicy.action(for: .notDetermined), .requestAndRegister)
    }

    func testAuthorizedRegistersWithoutPrompting() {
        XCTAssertEqual(PushPermissionPolicy.action(for: .authorized), .register)
    }

    func testProvisionalAndEphemeralRegisterWithoutPrompting() {
        XCTAssertEqual(PushPermissionPolicy.action(for: .provisional), .register)
        if #available(iOS 14.0, *) {
            XCTAssertEqual(PushPermissionPolicy.action(for: .ephemeral), .register)
        }
    }

    func testDeniedNeverPromptsAgain() {
        XCTAssertEqual(PushPermissionPolicy.action(for: .denied), .skip)
    }
}