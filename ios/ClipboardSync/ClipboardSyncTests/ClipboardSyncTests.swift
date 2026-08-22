import Foundation
import Testing
@testable import ClipboardSync

@Suite("Milestone 4 app behavior")
struct ClipboardSyncTests {
    private let session = AppSession(
        userID: UUID(uuidString: "11111111-1111-1111-1111-111111111111")!,
        email: "person@example.com"
    )

    @Test("Configuration accepts only a base project URL")
    func configurationRejectsRESTURL() {
        #expect(throws: ConfigurationError.invalidURL) {
            try AppConfiguration.validated(
                urlValue: "https://project-ref.supabase.co/rest/v1",
                keyValue: "sb_publishable_example"
            )
        }
    }

    @Test("Configuration rejects a new-format secret key")
    func configurationRejectsSecretKey() {
        #expect(throws: ConfigurationError.secretKeyNotAllowed) {
            try AppConfiguration.validated(
                urlValue: "https://project-ref.supabase.co",
                keyValue: "sb_secret_example"
            )
        }
    }

    @Test("Configuration rejects a legacy service-role JWT")
    func configurationRejectsLegacyServiceRoleKey() {
        let syntheticServiceRoleJWT = "e30.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.signature"

        #expect(throws: ConfigurationError.secretKeyNotAllowed) {
            try AppConfiguration.validated(
                urlValue: "https://project-ref.supabase.co",
                keyValue: syntheticServiceRoleJWT
            )
        }
    }

    @Test("Client device key is generated once and reused")
    func stableDeviceKey() {
        let suiteName = "ClipboardSyncTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let expected = UUID(uuidString: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")!
        let store = UserDefaultsDeviceIdentityStore(defaults: defaults) { expected }

        #expect(store.clientDeviceKey() == expected.uuidString.lowercased())
        #expect(store.clientDeviceKey() == expected.uuidString.lowercased())
    }

    @Test("Logout preserves the client device key")
    @MainActor
    func logoutPreservesDeviceKey() async {
        let identity = MemoryIdentityStore(value: "stable-install-key")
        let service = MockService(session: session)
        let model = makeModel(service: service, identity: identity)

        await model.signIn()
        model.draftText = "account-specific text"
        await model.logout()

        #expect(identity.clientDeviceKey() == "stable-install-key")
        #expect(model.screen == .signedOut)
        #expect(model.registeredDeviceID == nil)
        #expect(model.draftText.isEmpty)
        #expect(service.signOutCalled)
    }

    @Test("Initial empty session selects the sign-in screen")
    @MainActor
    func emptySessionRestoration() async {
        let service = MockService(session: session)
        let model = makeModel(service: service)
        model.start()

        service.emit(.initialSession(nil))
        await waitUntil { model.screen == .signedOut }

        #expect(model.screen == .signedOut)
    }

    @Test("Restored session selects sync screen and registers device")
    @MainActor
    func successfulSessionRestoration() async {
        let service = MockService(session: session)
        let model = makeModel(service: service)
        model.start()

        service.emit(.initialSession(session))
        await waitUntil { model.registeredDeviceID != nil }

        #expect(model.screen == .signedIn(session))
        #expect(service.deviceRequests.count == 1)
    }

    @Test("Email/password sign-in succeeds and clears the password")
    @MainActor
    func successfulLogin() async {
        let service = MockService(session: session)
        let model = makeModel(service: service)
        model.email = "  person@example.com  "
        model.password = "example-password"

        await model.signIn()

        #expect(service.lastLoginEmail == "person@example.com")
        #expect(service.lastLoginPassword == "example-password")
        #expect(model.password.isEmpty)
        #expect(model.screen == .signedIn(session))
        #expect(model.statusMessage == "Device ready.")
    }

    @Test("Failed login returns to sign-in with a readable error")
    @MainActor
    func failedLogin() async {
        let service = MockService(session: session)
        service.signInError = TestFailure(message: "Invalid login")
        let model = makeModel(service: service)
        model.email = "person@example.com"
        model.password = "wrong"

        await model.signIn()

        #expect(model.screen == .signedOut)
        #expect(model.errorMessage == "Invalid login")
        #expect(!model.isBusy)
    }

    @Test("Device upsert uses stable key, iPhone name, and iOS platform")
    @MainActor
    func deviceUpsertPayload() async {
        let service = MockService(session: session)
        let model = makeModel(
            service: service,
            identity: MemoryIdentityStore(value: "install-123"),
            deviceName: "Andy's iPhone"
        )

        await model.signIn()

        #expect(
            service.deviceRequests == [
                DeviceUpsertRequest(
                    clientDeviceKey: "install-123",
                    name: "Andy's iPhone",
                    platform: "ios"
                )
            ]
        )
        #expect(model.registeredDeviceID == service.defaultDeviceID)
    }

    @Test("Push re-upserts and uses a replacement stale-device ID")
    @MainActor
    func staleDeviceReplacement() async {
        let oldID = UUID(uuidString: "22222222-2222-2222-2222-222222222222")!
        let replacementID = UUID(uuidString: "33333333-3333-3333-3333-333333333333")!
        let service = MockService(session: session)
        service.deviceIDs = [oldID, replacementID]
        let model = makeModel(service: service)

        await model.signIn()
        model.draftText = "fresh text"
        await model.pushText()

        #expect(service.deviceRequests.count == 2)
        #expect(model.registeredDeviceID == replacementID)
        #expect(service.pushRequests.last?.sourceDeviceID == replacementID)
    }

    @Test("Whitespace-only text is rejected without a backend call")
    @MainActor
    func whitespaceOnlyPush() async {
        let service = MockService(session: session)
        let model = makeModel(service: service)
        model.draftText = "  \n\t  "

        await model.pushText()

        #expect(service.deviceRequests.isEmpty)
        #expect(service.pushRequests.isEmpty)
        #expect(model.errorMessage == "Enter text or copy some text to the clipboard before pushing.")
    }

    @Test("Empty draft reads and pushes text from the iPhone clipboard")
    @MainActor
    func emptyDraftUsesClipboardText() async {
        let service = MockService(session: session)
        let model = makeModel(service: service, clipboardText: "  clipboard spacing  ")

        await model.pushText()

        #expect(service.pushRequests.count == 1)
        #expect(service.pushRequests[0].content == "  clipboard spacing  ")
        #expect(model.draftText == "  clipboard spacing  ")
        #expect(model.statusMessage == "Text pushed successfully.")
    }

    @Test("Entered text takes priority without reading the clipboard")
    @MainActor
    func enteredTextDoesNotReadClipboard() async {
        let service = MockService(session: session)
        var clipboardWasRead = false
        let model = AppModel(
            service: service,
            identityStore: MemoryIdentityStore(value: "stable-key"),
            deviceName: "Test iPhone",
            clipboardTextProvider: {
                clipboardWasRead = true
                return "clipboard text"
            }
        )
        model.draftText = "entered text"

        await model.pushText()

        #expect(!clipboardWasRead)
        #expect(service.pushRequests.count == 1)
        #expect(service.pushRequests[0].content == "entered text")
        #expect(model.draftText == "entered text")
    }

    @Test("Push preserves valid text and sends text/plain")
    @MainActor
    func pushPayload() async {
        let service = MockService(session: session)
        let model = makeModel(service: service)
        model.draftText = "  keep my spacing  "

        await model.pushText()

        #expect(service.pushRequests.count == 1)
        #expect(service.pushRequests[0].content == "  keep my spacing  ")
        #expect(service.pushRequests[0].contentType == "text/plain")
        #expect(model.statusMessage == "Text pushed successfully.")
        #expect(!model.isBusy)
    }

    @Test("Push exposes a loading state until the backend completes")
    @MainActor
    func pushLoadingState() async {
        let (gate, continuation) = AsyncStream<Void>.makeStream()
        let service = MockService(session: session)
        service.pushWaiter = {
            for await _ in gate { return }
        }
        let model = makeModel(service: service)
        model.draftText = "wait for it"

        let pushTask = Task { await model.pushText() }
        await waitUntil { model.operation == .pushing }

        #expect(model.isBusy)
        #expect(model.operation == .pushing)

        continuation.yield()
        continuation.finish()
        await pushTask.value

        #expect(!model.isBusy)
        #expect(model.statusMessage == "Text pushed successfully.")
    }

    @Test("Pull requests newest item by descending creation time with limit one")
    @MainActor
    func latestPullQuery() async {
        let service = MockService(session: session)
        service.pullResult = ClipboardItem(
            id: UUID(),
            sourceDeviceID: nil,
            content: "newest",
            contentType: "text/plain",
            createdAt: .now
        )
        let model = makeModel(service: service)

        await model.pullLatest()

        #expect(service.pullQueries == [.latest])
        #expect(service.pullQueries[0].orderColumn == "created_at")
        #expect(service.pullQueries[0].ascending == false)
        #expect(service.pullQueries[0].limit == 1)
        #expect(model.pulledText == "newest")
        #expect(model.statusMessage == "Latest text pulled successfully.")
    }

    @Test("Empty pull result displays a friendly empty state")
    @MainActor
    func emptyPull() async {
        let service = MockService(session: session)
        service.pullResult = nil
        let model = makeModel(service: service)

        await model.pullLatest()

        #expect(model.pulledText == nil)
        #expect(model.statusMessage == "No synced text yet.")
        #expect(model.errorMessage == nil)
    }

    @Test("Push failure preserves draft and exposes an error state")
    @MainActor
    func pushFailureState() async {
        let service = MockService(session: session)
        service.pushError = TestFailure(message: "Network unavailable")
        let model = makeModel(service: service)
        model.draftText = "do not lose this"

        await model.pushText()

        #expect(model.draftText == "do not lose this")
        #expect(model.errorMessage == "Network unavailable")
        #expect(model.statusMessage == nil)
        #expect(!model.isBusy)
    }

    @Test("Offline push preserves draft and displays actionable feedback")
    @MainActor
    func offlinePush() async {
        let service = MockService(session: session)
        let model = makeModel(service: service)
        model.start()
        service.emit(.initialSession(session))
        await waitUntil { model.registeredDeviceID != nil }
        service.pushError = SyncServiceError.offline
        model.draftText = "retry this later"

        await model.pushText()

        #expect(model.draftText == "retry this later")
        #expect(model.errorMessage == "You appear to be offline. Check your connection and try again.")
        #expect(model.screen == .signedIn(session))
    }

    @Test("Expired session during pull returns to sign-in")
    @MainActor
    func expiredSessionDuringPull() async {
        let service = MockService(session: session)
        let model = makeModel(service: service)
        model.start()
        service.emit(.initialSession(session))
        await waitUntil { model.registeredDeviceID != nil }
        service.pullError = SyncServiceError.authenticationRequired

        await model.pullLatest()

        #expect(model.screen == .signedOut)
        #expect(model.errorMessage == "Your session expired. Sign in again.")
        #expect(model.registeredDeviceID == nil)
    }

    @Test("Offline URL error maps to a safe message")
    func offlineErrorMapping() {
        let result = SupabaseSyncService.mapError(
            URLError(.notConnectedToInternet),
            operation: .pullText
        )

        #expect(result == .offline)
        #expect(result.localizedDescription.contains("offline"))
    }

    @Test("Unexpected backend details are not shown to the user")
    func genericErrorMapping() {
        let result = SupabaseSyncService.mapError(
            TestFailure(message: "synthetic backend internals"),
            operation: .pushText
        )

        #expect(result == .operationFailed(.pushText))
        #expect(!result.localizedDescription.contains("synthetic"))
    }

    @MainActor
    private func makeModel(
        service: MockService,
        identity: MemoryIdentityStore = MemoryIdentityStore(value: "stable-key"),
        deviceName: String = "Test iPhone",
        clipboardText: String? = nil
    ) -> AppModel {
        AppModel(
            service: service,
            identityStore: identity,
            deviceName: deviceName,
            clipboardTextProvider: { clipboardText }
        )
    }

    @MainActor
    private func waitUntil(_ condition: @escaping @MainActor () -> Bool) async {
        for _ in 0..<100 where !condition() {
            await Task.yield()
        }
    }
}

private final class MemoryIdentityStore: DeviceIdentityStoring {
    private let value: String

    init(value: String) {
        self.value = value
    }

    func clientDeviceKey() -> String { value }
}

private final class MockService: ClipboardSyncServicing, @unchecked Sendable {
    let defaultDeviceID = UUID(uuidString: "99999999-9999-9999-9999-999999999999")!

    var signInError: Error?
    var signOutError: Error?
    var pushError: Error?
    var pullError: Error?
    var pushWaiter: (() async -> Void)?
    var deviceIDs: [UUID] = []
    var pullResult: ClipboardItem?

    private(set) var lastLoginEmail: String?
    private(set) var lastLoginPassword: String?
    private(set) var signOutCalled = false
    private(set) var deviceRequests: [DeviceUpsertRequest] = []
    private(set) var pushRequests: [ClipboardPushRequest] = []
    private(set) var pullQueries: [LatestClipboardQuery] = []

    private let session: AppSession
    private let stream: AsyncStream<AppAuthEvent>
    private let continuation: AsyncStream<AppAuthEvent>.Continuation

    init(session: AppSession) {
        self.session = session
        var capturedContinuation: AsyncStream<AppAuthEvent>.Continuation!
        stream = AsyncStream { capturedContinuation = $0 }
        continuation = capturedContinuation
    }

    var authEvents: AsyncStream<AppAuthEvent> { stream }

    func emit(_ event: AppAuthEvent) {
        continuation.yield(event)
    }

    func signIn(email: String, password: String) async throws -> AppSession {
        lastLoginEmail = email
        lastLoginPassword = password
        if let signInError { throw signInError }
        return session
    }

    func signOut() async throws {
        signOutCalled = true
        if let signOutError { throw signOutError }
    }

    func upsertDevice(_ request: DeviceUpsertRequest) async throws -> UUID {
        deviceRequests.append(request)
        if !deviceIDs.isEmpty { return deviceIDs.removeFirst() }
        return defaultDeviceID
    }

    func pushText(_ request: ClipboardPushRequest) async throws -> ClipboardItem {
        pushRequests.append(request)
        await pushWaiter?()
        if let pushError { throw pushError }
        return ClipboardItem(
            id: UUID(),
            sourceDeviceID: request.sourceDeviceID,
            content: request.content,
            contentType: request.contentType,
            createdAt: .now
        )
    }

    func pullLatest(query: LatestClipboardQuery) async throws -> ClipboardItem? {
        pullQueries.append(query)
        if let pullError { throw pullError }
        return pullResult
    }
}

private struct TestFailure: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}
