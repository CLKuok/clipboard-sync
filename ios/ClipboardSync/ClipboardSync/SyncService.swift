import Foundation

struct AppSession: Equatable, Sendable {
    let userID: UUID
    let email: String
}

enum AppAuthEvent: Equatable, Sendable {
    case initialSession(AppSession?)
    case signedIn(AppSession)
    case signedOut
}

struct DeviceUpsertRequest: Equatable, Sendable {
    let clientDeviceKey: String
    let name: String
    let platform: String

    init(clientDeviceKey: String, name: String, platform: String = "ios") {
        self.clientDeviceKey = clientDeviceKey
        self.name = name
        self.platform = platform
    }
}

struct ClipboardPushRequest: Equatable, Sendable {
    let sourceDeviceID: UUID
    let content: String
    let contentType: String

    init(sourceDeviceID: UUID, content: String, contentType: String = "text/plain") {
        self.sourceDeviceID = sourceDeviceID
        self.content = content
        self.contentType = contentType
    }
}

struct LatestClipboardQuery: Equatable, Sendable {
    let orderColumn: String
    let ascending: Bool
    let limit: Int

    static let latest = LatestClipboardQuery(
        orderColumn: "created_at",
        ascending: false,
        limit: 1
    )
}

struct ClipboardItem: Equatable, Sendable {
    let id: UUID
    let sourceDeviceID: UUID?
    let content: String
    let contentType: String
    let createdAt: Date
}

protocol ClipboardSyncServicing: Sendable {
    var authEvents: AsyncStream<AppAuthEvent> { get }

    func signIn(email: String, password: String) async throws -> AppSession
    func signOut() async throws
    func upsertDevice(_ request: DeviceUpsertRequest) async throws -> UUID
    func pushText(_ request: ClipboardPushRequest) async throws -> ClipboardItem
    func pullLatest(query: LatestClipboardQuery) async throws -> ClipboardItem?
}
