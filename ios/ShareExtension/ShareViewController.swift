import UIKit

class ShareViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
        // Real implementation lands in Task 11.
        extensionContext?.completeRequest(returningItems: nil)
    }
}
