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

    // MARK: - Slice 2 writes

    private func routedClient(getBody: String, onWrite: @escaping (URLRequest) -> (Int, String)) -> APIClient {
        StubURLProtocol.handler = { req in
            let method = req.httpMethod ?? "GET"
            let path = req.url?.path ?? ""
            let (status, body): (Int, String)
            if method == "GET", path == "/api/v1/events" {
                (status, body) = (200, getBody)
            } else {
                (status, body) = onWrite(req)
            }
            return (HTTPURLResponse(url: req.url!, statusCode: status, httpVersion: nil, headerFields: nil)!,
                    Data(body.utf8))
        }
        return APIClient(baseURL: URL(string: "http://t.local")!,
                         session: StubURLProtocol.session(),
                         tokenProvider: { "tok" })
    }

    private static func date(offset: Int) -> Date {
        Calendar.current.date(byAdding: .day, value: offset, to: Date())!
    }

    private func bodyJSON(_ req: URLRequest) -> [String: Any] {
        (try? JSONSerialization.jsonObject(with: req.httpBody ?? Data()) as? [String: Any]) ?? [:]
    }

    func testCreateInsertsIntoCorrectPartition() async {
        // @spec IOS-EVT-006
        var captured: [String: Any] = [:]
        let vm = EventsViewModel(client: routedClient(
            getBody: #"{"events":[\#(self.eventJSON(id: 1, dayOffset: 1))]}"#,
            onWrite: { req in
                captured = self.bodyJSON(req)
                XCTAssertEqual(req.httpMethod, "POST")
                XCTAssertEqual(req.url?.path, "/api/v1/events")
                return (201, #"{"event":\#(self.eventJSON(id: 2, dayOffset: -1))}"#)
            }))
        await vm.load()
        let ok = await vm.create(name: "Past Party", date: Self.date(offset: -1))
        XCTAssertTrue(ok)
        XCTAssertEqual(captured["name"] as? String, "Past Party")
        XCTAssertEqual(captured["date"] as? String, Self.dayString(offset: -1))
        XCTAssertEqual(vm.upcoming.map(\.id), [1])
        XCTAssertEqual(vm.past.map(\.id), [2])
        XCTAssertNil(vm.error)
    }

    func testCreateSurfacesValidationMessage() async {
        // @spec IOS-EVT-006, IOS-EVT-010
        let vm = EventsViewModel(client: routedClient(
            getBody: #"{"events":[\#(self.eventJSON(id: 1, dayOffset: 1))]}"#,
            onWrite: { _ in (400, #"{"errors":["Event name is required."]}"#) }))
        await vm.load()
        let ok = await vm.create(name: "", date: Self.date(offset: 1))
        XCTAssertFalse(ok)
        XCTAssertEqual(vm.error, "Event name is required.")
        XCTAssertEqual(vm.upcoming.map(\.id), [1])
        XCTAssertTrue(vm.past.isEmpty)
    }

    func testUpdateReplacesInPlace() async {
        // @spec IOS-EVT-007
        var captured: [String: Any] = [:]
        let vm = EventsViewModel(client: routedClient(
            getBody: #"{"events":[\#(self.eventJSON(id: 1, dayOffset: 1)),\#(self.eventJSON(id: 2, dayOffset: 3))]}"#,
            onWrite: { req in
                captured = self.bodyJSON(req)
                XCTAssertEqual(req.httpMethod, "PATCH")
                XCTAssertEqual(req.url?.path, "/api/v1/events/1")
                return (200, #"{"event":{"id":1,"name":"Renamed","date":"\#(Self.dayString(offset: 1))","created_by":{"id":2,"name":"Mom"},"item_count":0}}"#)
            }))
        await vm.load()
        let ok = await vm.update(id: 1, name: "Renamed", date: Self.date(offset: 1))
        XCTAssertTrue(ok)
        XCTAssertEqual(captured["name"] as? String, "Renamed")
        XCTAssertEqual(vm.upcoming.map(\.id), [1, 2])
        XCTAssertEqual(vm.upcoming.first?.name, "Renamed")
    }

    func testDeleteRemovesFromList() async {
        // @spec IOS-EVT-008
        var deletedMethod: String?
        var deletedPath: String?
        let vm = EventsViewModel(client: routedClient(
            getBody: #"{"events":[\#(self.eventJSON(id: 1, dayOffset: 1)),\#(self.eventJSON(id: 2, dayOffset: -1))]}"#,
            onWrite: { req in
                deletedMethod = req.httpMethod
                deletedPath = req.url?.path
                return (200, #"{"ok":true}"#)
            }))
        await vm.load()
        guard let event = vm.upcoming.first(where: { $0.id == 1 }) else {
            XCTFail("expected event 1"); return
        }
        await vm.delete(event)
        XCTAssertEqual(deletedMethod, "DELETE")
        XCTAssertEqual(deletedPath, "/api/v1/events/1")
        XCTAssertTrue(vm.upcoming.isEmpty)
        XCTAssertEqual(vm.past.map(\.id), [2])
        XCTAssertNil(vm.error)
    }

    func testDeleteForbiddenSurfacesFriendlyErrorAndReloads() async {
        // @spec IOS-EVT-010
        let vm = EventsViewModel(client: routedClient(
            getBody: #"{"events":[\#(self.eventJSON(id: 1, dayOffset: 1))]}"#,
            onWrite: { _ in (403, #"{"error":"forbidden"}"#) }))
        await vm.load()
        guard let event = vm.upcoming.first else { XCTFail("expected event"); return }
        await vm.delete(event)
        XCTAssertEqual(vm.error, "You can only delete events you created.")
        XCTAssertEqual(vm.upcoming.map(\.id), [1])
    }

    func testUpdateNotFoundSurfacesFriendlyErrorAndReloads() async {
        // @spec IOS-EVT-010
        let vm = EventsViewModel(client: routedClient(
            getBody: #"{"events":[\#(self.eventJSON(id: 1, dayOffset: 1))]}"#,
            onWrite: { _ in (404, #"{"error":"not_found"}"#) }))
        await vm.load()
        let ok = await vm.update(id: 1, name: "Gone", date: Self.date(offset: 1))
        XCTAssertFalse(ok)
        XCTAssertEqual(vm.error, "That event no longer exists.")
        XCTAssertEqual(vm.upcoming.map(\.id), [1])
    }
}
