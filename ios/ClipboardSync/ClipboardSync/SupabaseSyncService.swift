import Foundation
import Supabase

final class SupabaseSyncService: ClipboardSyncServicing, @unchecked Sendable {
    private let client: SupabaseClient

    init(configuration: AppConfiguration) {
        client = SupabaseClient(
            supabaseURL: configuration.supabaseURL,
            supabaseKey: configuration.supabaseAnonKey
        )
    }

    var authEvents: AsyncStream<AppAuthEvent> {
        AsyncStream { continuation in
            let task = Task { [client] in
                for await (event, session) in client.auth.authStateChanges {
                    guard !Task.isCancelled else { return }

                    switch event {
                    case .initialSession:
                        continuation.yield(.initialSession(session.map(Self.mapSession)))
                    case .signedIn:
                        if let session {
                            continuation.yield(.signedIn(Self.mapSession(session)))
                        }
                    case .signedOut, .userDeleted:
                        continuation.yield(.signedOut)
                    default:
                        break
                    }
                }
                continuation.finish()
            }

            continuation.onTermination = { _ in task.cancel() }
        }
    }

    func signIn(email: String, password: String) async throws -> AppSession {
        do {
            let session = try await client.auth.signIn(email: email, password: password)
            return Self.mapSession(session)
        } catch {
            throw Self.mapError(error, operation: .signIn)
        }
    }

    func signOut() async throws {
        do {
            try await client.auth.signOut()
        } catch {
            throw Self.mapError(error, operation: .signOut)
        }
    }

    func upsertDevice(_ request: DeviceUpsertRequest) async throws -> UUID {
        let payload = DevicePayload(
            clientDeviceKey: request.clientDeviceKey,
            name: request.name,
            platform: request.platform,
            lastSeenAt: Date()
        )

        do {
            let row: DeviceRow = try await client
                .from("devices")
                .upsert(payload, onConflict: "user_id,client_device_key")
                .select("id")
                .single()
                .execute()
                .value

            return row.id
        } catch {
            throw Self.mapError(error, operation: .registerDevice)
        }
    }

    func pushText(_ request: ClipboardPushRequest) async throws -> ClipboardItem {
        let payload = ClipboardPayload(
            sourceDeviceID: request.sourceDeviceID,
            content: request.content,
            contentType: request.contentType
        )

        do {
            let row: ClipboardRow = try await client
                .from("clipboard_items")
                .insert(payload)
                .select("id,source_device_id,content,content_type,created_at")
                .single()
                .execute()
                .value

            return row.item
        } catch {
            throw Self.mapError(error, operation: .pushText)
        }
    }

    func pullLatest(query: LatestClipboardQuery) async throws -> ClipboardItem? {
        do {
            let rows: [ClipboardRow] = try await client
                .from("clipboard_items")
                .select("id,source_device_id,content,content_type,created_at")
                .order(query.orderColumn, ascending: query.ascending)
                .limit(query.limit)
                .execute()
                .value

            return rows.first?.item
        } catch {
            throw Self.mapError(error, operation: .pullText)
        }
    }

    static func mapError(_ error: Error, operation: SyncOperation) -> SyncServiceError {
        if isOffline(error) {
            return .offline
        }

        if let authError = error as? AuthError {
            if operation == .signIn, authError.errorCode == .invalidCredentials {
                return .invalidCredentials
            }

            let authenticationCodes: Set<ErrorCode> = [
                .badJWT,
                .invalidJWT,
                .noAuthorization,
                .refreshTokenAlreadyUsed,
                .refreshTokenNotFound,
                .sessionExpired,
                .sessionNotFound,
                .userNotFound,
            ]
            if authenticationCodes.contains(authError.errorCode) {
                return .authenticationRequired
            }
        }

        return .operationFailed(operation)
    }

    private static func isOffline(_ error: Error) -> Bool {
        var current: NSError? = error as NSError
        var visited: Set<ObjectIdentifier> = []
        let offlineCodes: Set<Int> = [
            URLError.cannotConnectToHost.rawValue,
            URLError.cannotFindHost.rawValue,
            URLError.dataNotAllowed.rawValue,
            URLError.dnsLookupFailed.rawValue,
            URLError.internationalRoamingOff.rawValue,
            URLError.networkConnectionLost.rawValue,
            URLError.notConnectedToInternet.rawValue,
            URLError.timedOut.rawValue,
        ]

        while let candidate = current {
            let identifier = ObjectIdentifier(candidate)
            guard visited.insert(identifier).inserted else { break }
            if candidate.domain == NSURLErrorDomain, offlineCodes.contains(candidate.code) {
                return true
            }
            current = candidate.userInfo[NSUnderlyingErrorKey] as? NSError
        }

        return false
    }

    private static func mapSession(_ session: Session) -> AppSession {
        AppSession(
            userID: session.user.id,
            email: session.user.email ?? "Signed-in user"
        )
    }
}

private struct DevicePayload: Encodable {
    let clientDeviceKey: String
    let name: String
    let platform: String
    let lastSeenAt: Date

    enum CodingKeys: String, CodingKey {
        case clientDeviceKey = "client_device_key"
        case name
        case platform
        case lastSeenAt = "last_seen_at"
    }
}

private struct DeviceRow: Decodable {
    let id: UUID
}

private struct ClipboardPayload: Encodable {
    let sourceDeviceID: UUID
    let content: String
    let contentType: String

    enum CodingKeys: String, CodingKey {
        case sourceDeviceID = "source_device_id"
        case content
        case contentType = "content_type"
    }
}

private struct ClipboardRow: Decodable {
    let id: UUID
    let sourceDeviceID: UUID?
    let content: String
    let contentType: String
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case sourceDeviceID = "source_device_id"
        case content
        case contentType = "content_type"
        case createdAt = "created_at"
    }

    var item: ClipboardItem {
        ClipboardItem(
            id: id,
            sourceDeviceID: sourceDeviceID,
            content: content,
            contentType: contentType,
            createdAt: createdAt
        )
    }
}
