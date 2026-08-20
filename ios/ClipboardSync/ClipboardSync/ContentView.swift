import SwiftUI
import UIKit

struct ContentView: View {
    let configuration: Result<AppConfiguration, ConfigurationError>

    var body: some View {
        switch configuration {
        case .success(let configuration):
            AppRootView(configuration: configuration)
        case .failure(let error):
            ConfigurationErrorView(message: error.localizedDescription)
        }
    }
}

private struct AppRootView: View {
    @StateObject private var model: AppModel

    init(configuration: AppConfiguration) {
        _model = StateObject(
            wrappedValue: AppModel(
                service: SupabaseSyncService(configuration: configuration),
                identityStore: UserDefaultsDeviceIdentityStore(),
                deviceName: UIDevice.current.name
            )
        )
    }

    var body: some View {
        Group {
            switch model.screen {
            case .restoringSession:
                ProgressView("Restoring session…")
            case .signedOut, .signingIn:
                LoginView(model: model)
            case .signedIn(let session):
                SyncView(model: model, session: session)
            }
        }
        .task { model.start() }
    }
}

private struct LoginView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Email", text: $model.email)
                        .textContentType(.username)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()

                    SecureField("Password", text: $model.password)
                        .textContentType(.password)
                } header: {
                    Text("Supabase account")
                } footer: {
                    Text("Use an existing email/password account from this project's Supabase Auth users.")
                }

                if let error = model.errorMessage {
                    FeedbackView(message: error, isError: true)
                }

                Button {
                    Task { await model.signIn() }
                } label: {
                    HStack {
                        Spacer()
                        if model.screen == .signingIn {
                            ProgressView()
                        } else {
                            Text("Sign In")
                        }
                        Spacer()
                    }
                }
                .disabled(
                    model.isBusy
                        || model.email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                        || model.password.isEmpty
                )
            }
            .navigationTitle("Clipboard Sync")
        }
    }
}

private struct SyncView: View {
    @ObservedObject var model: AppModel
    let session: AppSession

    var body: some View {
        NavigationStack {
            Form {
                Section("Signed in") {
                    Text(session.email)
                        .textSelection(.enabled)
                }

                Section("Text to push") {
                    TextEditor(text: $model.draftText)
                        .frame(minHeight: 130)
                        .accessibilityLabel("Text to push")

                    Button("Push Text") {
                        Task { await model.pushText() }
                    }
                    .disabled(model.isBusy)
                }

                Section("Latest synced text") {
                    if let text = model.pulledText {
                        Text(text)
                            .textSelection(.enabled)
                    } else {
                        Text("Nothing pulled yet.")
                            .foregroundStyle(.secondary)
                    }

                    Button("Pull Latest") {
                        Task { await model.pullLatest() }
                    }
                    .disabled(model.isBusy)
                }

                if model.isBusy {
                    HStack {
                        ProgressView()
                        Text(progressMessage)
                    }
                }

                if let message = model.statusMessage {
                    FeedbackView(message: message, isError: false)
                }

                if let error = model.errorMessage {
                    FeedbackView(message: error, isError: true)
                }

                Section {
                    Button("Log Out", role: .destructive) {
                        Task { await model.logout() }
                    }
                    .disabled(model.isBusy)
                }
            }
            .navigationTitle("Manual Sync")
        }
    }

    private var progressMessage: String {
        switch model.operation {
        case .registeringDevice: "Registering this iPhone…"
        case .pushing: "Pushing text…"
        case .pulling: "Pulling latest text…"
        case .signingOut: "Signing out…"
        case nil: "Working…"
        }
    }
}

private struct FeedbackView: View {
    let message: String
    let isError: Bool

    var body: some View {
        Label(message, systemImage: isError ? "exclamationmark.triangle" : "checkmark.circle")
            .foregroundStyle(isError ? .red : .green)
            .accessibilityLabel(isError ? "Error: \(message)" : "Success: \(message)")
    }
}

private struct ConfigurationErrorView: View {
    let message: String

    var body: some View {
        ContentUnavailableView {
            Label("Configuration needed", systemImage: "gearshape")
        } description: {
            Text(message)
        } actions: {
            Text("See ios/README.md for setup steps.")
                .font(.footnote)
        }
        .padding()
    }
}

#Preview {
    ContentView(configuration: .failure(.missingValue("SUPABASE_URL")))
}
