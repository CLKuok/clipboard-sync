import Combine
import Foundation

@MainActor
final class AppModel: ObservableObject {
    enum Screen: Equatable {
        case restoringSession
        case signedOut
        case signingIn
        case signedIn(AppSession)
    }

    enum Operation: Equatable {
        case registeringDevice
        case pushing
        case pulling
        case signingOut
    }

    @Published private(set) var screen: Screen = .restoringSession
    @Published private(set) var operation: Operation?
    @Published private(set) var statusMessage: String?
    @Published private(set) var errorMessage: String?
    @Published private(set) var pulledText: String?
    @Published var email = ""
    @Published var password = ""
    @Published var draftText = ""

    private(set) var registeredDeviceID: UUID?

    var isBusy: Bool { operation != nil || screen == .signingIn }

    private let service: ClipboardSyncServicing
    private let identityStore: DeviceIdentityStoring
    private let deviceName: String
    private var authTask: Task<Void, Never>?
    private var establishingUserID: UUID?

    init(
        service: ClipboardSyncServicing,
        identityStore: DeviceIdentityStoring,
        deviceName: String
    ) {
        self.service = service
        self.identityStore = identityStore
        self.deviceName = deviceName
    }

    func start() {
        guard authTask == nil else { return }

        authTask = Task { [weak self, service] in
            for await event in service.authEvents {
                guard let self, !Task.isCancelled else { return }
                await self.handleAuthEvent(event)
            }
        }
    }

    func signIn() async {
        guard !isBusy else { return }
        clearFeedback()
        screen = .signingIn

        do {
            let session = try await service.signIn(
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                password: password
            )
            password = ""
            await establishSession(session)
        } catch {
            screen = .signedOut
            errorMessage = userMessage(for: error)
        }
    }

    func logout() async {
        guard !isBusy else { return }
        clearFeedback()
        operation = .signingOut

        do {
            try await service.signOut()
            applySignedOutState()
        } catch {
            operation = nil
            errorMessage = userMessage(for: error)
        }
    }

    func pushText() async {
        guard !isBusy else { return }
        guard !draftText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            errorMessage = "Enter or paste some text before pushing."
            statusMessage = nil
            return
        }

        clearFeedback()
        operation = .pushing

        do {
            let refreshedDeviceID = try await service.upsertDevice(deviceRequest())
            registeredDeviceID = refreshedDeviceID
            _ = try await service.pushText(
                ClipboardPushRequest(
                    sourceDeviceID: refreshedDeviceID,
                    content: draftText
                )
            )
            statusMessage = "Text pushed successfully."
        } catch {
            errorMessage = userMessage(for: error)
        }

        operation = nil
    }

    func pullLatest() async {
        guard !isBusy else { return }
        clearFeedback()
        operation = .pulling

        do {
            if let item = try await service.pullLatest(query: .latest) {
                pulledText = item.content
                statusMessage = "Latest text pulled successfully."
            } else {
                pulledText = nil
                statusMessage = "No synced text yet."
            }
        } catch {
            errorMessage = userMessage(for: error)
        }

        operation = nil
    }

    private func handleAuthEvent(_ event: AppAuthEvent) async {
        switch event {
        case .initialSession(nil), .signedOut:
            applySignedOutState()
        case .initialSession(let session?):
            await establishSession(session)
        case .signedIn(let session):
            await establishSession(session)
        }
    }

    private func establishSession(_ session: AppSession) async {
        guard establishingUserID != session.userID else {
            screen = .signedIn(session)
            return
        }

        if case .signedIn(let current) = screen,
           current.userID == session.userID,
           registeredDeviceID != nil {
            screen = .signedIn(session)
            return
        }

        if case .signedIn(let current) = screen, current.userID != session.userID {
            registeredDeviceID = nil
        }

        screen = .signedIn(session)
        clearFeedback()
        operation = .registeringDevice
        establishingUserID = session.userID

        do {
            registeredDeviceID = try await service.upsertDevice(deviceRequest())
            statusMessage = "Device ready."
        } catch {
            errorMessage = "Signed in, but device registration failed: \(userMessage(for: error))"
        }

        establishingUserID = nil
        operation = nil
    }

    private func applySignedOutState() {
        screen = .signedOut
        operation = nil
        establishingUserID = nil
        registeredDeviceID = nil
        password = ""
        draftText = ""
        pulledText = nil
        clearFeedback()
    }

    private func deviceRequest() -> DeviceUpsertRequest {
        DeviceUpsertRequest(
            clientDeviceKey: identityStore.clientDeviceKey(),
            name: deviceName
        )
    }

    private func clearFeedback() {
        statusMessage = nil
        errorMessage = nil
    }

    private func userMessage(for error: Error) -> String {
        let message = error.localizedDescription.trimmingCharacters(in: .whitespacesAndNewlines)
        return message.isEmpty ? "Something went wrong. Please try again." : message
    }
}
