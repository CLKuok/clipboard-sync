import Foundation

struct AppConfiguration: Equatable, Sendable {
    let supabaseURL: URL
    let supabaseAnonKey: String

    static func load(from bundle: Bundle = .main) -> Result<AppConfiguration, ConfigurationError> {
        do {
            let urlValue = try requiredValue(named: "SUPABASE_URL", in: bundle)
            let keyValue = try requiredValue(named: "SUPABASE_ANON_KEY", in: bundle)
            return .success(try validated(urlValue: urlValue, keyValue: keyValue))
        } catch let error as ConfigurationError {
            return .failure(error)
        } catch {
            return .failure(.invalidURL)
        }
    }

    static func validated(urlValue: String, keyValue: String) throws -> AppConfiguration {
        guard
            let url = URL(string: urlValue),
            let scheme = url.scheme?.lowercased(),
            scheme == "https",
            url.host != nil,
            url.path.isEmpty || url.path == "/",
            url.query == nil,
            url.fragment == nil,
            url.user == nil,
            url.password == nil
        else {
            throw ConfigurationError.invalidURL
        }

        guard !urlValue.contains("your-project-ref") else {
            throw ConfigurationError.missingValue("SUPABASE_URL")
        }

        guard !keyValue.contains("your-publishable-or-anon-key") else {
            throw ConfigurationError.missingValue("SUPABASE_ANON_KEY")
        }

        guard !isSecretKey(keyValue) else {
            throw ConfigurationError.secretKeyNotAllowed
        }

        return AppConfiguration(supabaseURL: url, supabaseAnonKey: keyValue)
    }

    private static func requiredValue(named name: String, in bundle: Bundle) throws -> String {
        guard let value = bundle.object(forInfoDictionaryKey: name) as? String else {
            throw ConfigurationError.missingValue(name)
        }

        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !trimmed.contains("$(") else {
            throw ConfigurationError.missingValue(name)
        }
        return trimmed
    }

    private static func isSecretKey(_ key: String) -> Bool {
        if key.lowercased().hasPrefix("sb_secret_") {
            return true
        }

        let parts = key.split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count == 3 else { return false }

        var encodedPayload = String(parts[1])
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        encodedPayload += String(repeating: "=", count: (4 - encodedPayload.count % 4) % 4)

        guard
            let data = Data(base64Encoded: encodedPayload),
            let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let role = object["role"] as? String
        else {
            return false
        }

        return role == "service_role"
    }
}

enum ConfigurationError: LocalizedError, Equatable {
    case missingValue(String)
    case invalidURL
    case secretKeyNotAllowed

    var errorDescription: String? {
        switch self {
        case .missingValue(let name):
            "Missing \(name). Add it to Config/Supabase.xcconfig."
        case .invalidURL:
            "SUPABASE_URL must be the HTTPS project base URL, without /rest/v1."
        case .secretKeyNotAllowed:
            "A secret/service-role key must never be used in the iPhone app. Use the publishable or legacy anon key."
        }
    }
}
