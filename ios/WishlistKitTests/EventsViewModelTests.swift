import XCTest
@testable import WishlistKit

@MainActor
final class EventsViewModelTests: XCTestCase {
    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    private static func dayString(offset: Int) -> String {
        let date = Calendar.current.date(byAdding: .day, value: offset, to: Date())!
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }

    private func client(json: @escaping () -> (Int, String)) -> APIClient {
        StubURLProtocol.handler = { req in
            let (status, body) = json()
            return (HTTPURLResponse(url: req.url!, statusCode: status, httpVersion: nil, headerFields: nil)!,
                    Data(body.utf8))
        }
        return APIClient(baseURL: URL(string: "http://t.local")!,
                         session: StubURLProtocol.session(),
                         tokenProvider: { "tok" })
    }

    private func eventJSON(id: Int, dayOffset: Int) -> String {
        #"{"id":\#(id),"name":"E\#(id)","date":"\#(Self.dayString(offset: dayOffset))","created_by":{"id":2,"name":"Mom"},"item_count":0}"#
    }

    func testLoadPartitionsTodayIntoUpcoming() async {
        // @spec IOS-EVT-001, IOS-EVT-005
        let vm = EventsViewModel(client: client {
            (200, #"{"events":[\#(self.eventJSON(id: 1, dayOffset: -1)),\#(self.eventJSON(id: 2, dayOffset: 0)),\#(self.eventJSON(id: 3, dayOffset: 2)),\#(self.eventJSON(id: 4, dayOffset: 1))]}"#)
        })
        await vm.load()
        XCTAssertEqual(vm.upcoming.map(\.id), [2, 4, 3])
        XCTAssertEqual(vm.past.map(\.id), [1])
        XCTAssertNil(vm.error)
    }

    func testErrorThenRetryClears() async {
        // @spec IOS-EVT-004
        var failing = true
        let vm = EventsViewModel(client: client {
            failing ? (500, #"{"error":"boom"}"#)
                    : (200, #"{"events":[\#(self.eventJSON(id: 9, dayOffset: 1))]}"#)
        })
        await vm.load()
        XCTAssertEqual(vm.error, "Couldn't load events.")
        XCTAssertTrue(vm.upcoming.isEmpty)
        failing = false
        await vm.load()
        XCTAssertNil(vm.error)
        XCTAssertEqual(vm.upcoming.map(\.id), [9])
    }

    func testReloadReplacesLists() async {
        // @spec IOS-EVT-001
        var first = true
        let vm = EventsViewModel(client: client {
            first ? (200, #"{"events":[\#(self.eventJSON(id: 1, dayOffset: 1)),\#(self.eventJSON(id: 2, dayOffset: -1))]}"#)
                  : (200, #"{"events":[\#(self.eventJSON(id: 3, dayOffset: 5))]}"#)
        })
        await vm.load()
        XCTAssertEqual(vm.upcoming.map(\.id), [1])
        XCTAssertEqual(vm.past.map(\.id), [2])
        first = false
        await vm.load()
        XCTAssertEqual(vm.upcoming.map(\.id), [3])
        XCTAssertTrue(vm.past.isEmpty)
    }
}
