import Foundation

protocol DeviceIdentityStoring: AnyObject {
    func clientDeviceKey() -> String
}

final class UserDefaultsDeviceIdentityStore: DeviceIdentityStoring {
    private let defaults: UserDefaults
    private let storageKey: String
    private let makeUUID: () -> UUID

    init(
        defaults: UserDefaults = .standard,
        storageKey: String = "client_device_key",
        makeUUID: @escaping () -> UUID = UUID.init
    ) {
        self.defaults = defaults
        self.storageKey = storageKey
        self.makeUUID = makeUUID
    }

    func clientDeviceKey() -> String {
        if let existing = defaults.string(forKey: storageKey), !existing.isEmpty {
            return existing
        }

        let generated = makeUUID().uuidString.lowercased()
        defaults.set(generated, forKey: storageKey)
        return generated
    }
}
