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

private enum AppTheme {
    static let brand = Color(red: 37 / 255, green: 99 / 255, blue: 235 / 255)
    static let accent = Color(red: 6 / 255, green: 182 / 255, blue: 212 / 255)
    static let background = Color(uiColor: .systemGroupedBackground)
    static let surface = Color(uiColor: .secondarySystemGroupedBackground)
    static let border = Color(red: 220 / 255, green: 230 / 255, blue: 242 / 255)
    static let success = Color(red: 21 / 255, green: 128 / 255, blue: 61 / 255)
    static let error = Color(red: 180 / 255, green: 35 / 255, blue: 24 / 255)
}

private struct AppRootView: View {
    @StateObject private var model: AppModel

    init(configuration: AppConfiguration) {
        _model = StateObject(
            wrappedValue: AppModel(
                service: SupabaseSyncService(configuration: configuration),
                identityStore: UserDefaultsDeviceIdentityStore(),
                deviceName: UIDevice.current.name,
                clipboardTextProvider: { UIPasteboard.general.string }
            )
        )
    }

    var body: some View {
        Group {
            switch model.screen {
            case .restoringSession:
                RestoringSessionView()
            case .signedOut, .signingIn:
                LoginView(model: model)
            case .signedIn(let session):
                SyncView(model: model, session: session)
            }
        }
        .tint(AppTheme.brand)
        .task { model.start() }
    }
}

private struct LoginView: View {
    @ObservedObject var model: AppModel

    private var canSignIn: Bool {
        !model.isBusy
            && !model.email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !model.password.isEmpty
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    BrandHeader()

                    AppCard(
                        title: "Sign in to sync",
                        subtitle: "Use the same Supabase account on both devices."
                    ) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Email")
                                .font(.subheadline.weight(.medium))
                            TextField("you@example.com", text: $model.email)
                                .textContentType(.username)
                                .keyboardType(.emailAddress)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .submitLabel(.next)
                                .textFieldStyle(.roundedBorder)

                            Text("Password")
                                .font(.subheadline.weight(.medium))
                                .padding(.top, 4)
                            SecureField("Password", text: $model.password)
                                .textContentType(.password)
                                .submitLabel(.go)
                                .textFieldStyle(.roundedBorder)
                                .onSubmit(signIn)

                            PrimaryActionButton(
                                title: "Sign In",
                                systemImage: "arrow.right",
                                showsProgress: model.screen == .signingIn,
                                disabled: !canSignIn,
                                action: signIn
                            )
                            .padding(.top, 8)
                        }
                    }

                    if let error = model.errorMessage {
                        FeedbackBanner(message: error, kind: .error)
                    }
                }
                .frame(maxWidth: 620)
                .padding(.horizontal, 20)
                .padding(.vertical, 24)
            }
            .background(AppTheme.background.ignoresSafeArea())
            .background(KeyboardDismissHandler())
            .scrollDismissesKeyboard(.interactively)
            .toolbar(.hidden, for: .navigationBar)
        }
    }

    private func signIn() {
        guard canSignIn else { return }
        Task { await model.signIn() }
    }
}

private struct SyncView: View {
    @ObservedObject var model: AppModel
    let session: AppSession

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    BrandHeader()
                    accountCard
                    pushCard
                    pullCard

                    if model.isBusy {
                        ProgressBanner(message: progressMessage)
                    }

                    if let message = model.statusMessage {
                        FeedbackBanner(
                            message: message,
                            kind: message == "No synced text yet." ? .info : .success
                        )
                    }

                    if let error = model.errorMessage {
                        FeedbackBanner(message: error, kind: .error)
                    }

                    Button("Log Out", role: .destructive) {
                        Task { await model.logout() }
                    }
                    .font(.subheadline.weight(.medium))
                    .disabled(model.isBusy)
                    .padding(.vertical, 4)
                }
                .frame(maxWidth: 620)
                .padding(.horizontal, 20)
                .padding(.vertical, 24)
            }
            .background(AppTheme.background.ignoresSafeArea())
            .background(KeyboardDismissHandler())
            .scrollDismissesKeyboard(.interactively)
            .toolbar(.hidden, for: .navigationBar)
        }
    }

    private var accountCard: some View {
        AppCard {
            HStack(spacing: 12) {
                Image(systemName: "person.crop.circle.fill")
                    .font(.title2)
                    .foregroundStyle(AppTheme.brand)
                    .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Signed in")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(session.email)
                        .font(.subheadline.weight(.semibold))
                        .textSelection(.enabled)
                }
                Spacer()
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(AppTheme.success)
                    .accessibilityLabel("Device ready")
            }
        }
    }

    private var pushCard: some View {
        AppCard(
            title: "Push",
            subtitle: "Send entered or pasted text to your synced devices."
        ) {
            VStack(spacing: 12) {
                TextEditor(text: $model.draftText)
                    .frame(minHeight: 132)
                    .padding(8)
                    .scrollContentBackground(.hidden)
                    .background(Color(uiColor: .tertiarySystemGroupedBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(AppTheme.border, lineWidth: 1)
                    }
                    .accessibilityLabel("Text to push")

                PrimaryActionButton(
                    title: "Push Text",
                    systemImage: "arrow.up",
                    disabled: model.isBusy
                ) {
                    Task { await model.pushText() }
                }
            }
        }
    }

    private var pullCard: some View {
        AppCard(
            title: "Pull latest",
            subtitle: "Get the newest text synced from either device."
        ) {
            VStack(alignment: .leading, spacing: 12) {
                if let text = model.pulledText {
                    Text(text)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .background(Color(uiColor: .tertiarySystemGroupedBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                        .textSelection(.enabled)
                        .accessibilityLabel("Latest synced text")
                } else {
                    Label("Nothing pulled yet.", systemImage: "clipboard")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 6)
                }

                SecondaryActionButton(
                    title: "Pull Latest",
                    systemImage: "arrow.down",
                    disabled: model.isBusy
                ) {
                    Task { await model.pullLatest() }
                }
            }
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

private struct BrandHeader: View {
    var body: some View {
        HStack(spacing: 14) {
            Image("BrandMark")
                .resizable()
                .scaledToFit()
                .frame(width: 62, height: 62)
                .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 3) {
                Text("Clipboard Sync")
                    .font(.title.bold())
                    .foregroundStyle(.primary)
                Text("Move text between your iPhone and Windows PC.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct AppCard<Content: View>: View {
    let title: String?
    let subtitle: String?
    let content: Content

    init(
        title: String? = nil,
        subtitle: String? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.title = title
        self.subtitle = subtitle
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            if let title {
                VStack(alignment: .leading, spacing: 3) {
                    Text(title)
                        .font(.headline)
                    if let subtitle {
                        Text(subtitle)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(AppTheme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(AppTheme.border.opacity(0.8), lineWidth: 1)
        }
    }
}

private struct PrimaryActionButton: View {
    let title: String
    let systemImage: String
    var showsProgress = false
    var disabled = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Spacer()
                if showsProgress {
                    ProgressView()
                        .tint(.white)
                } else {
                    Label(title, systemImage: systemImage)
                }
                Spacer()
            }
            .font(.headline)
        }
        .buttonStyle(.borderedProminent)
        .buttonBorderShape(.roundedRectangle(radius: 10))
        .controlSize(.large)
        .tint(AppTheme.brand)
        .disabled(disabled)
    }
}

private struct SecondaryActionButton: View {
    let title: String
    let systemImage: String
    var disabled = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Spacer()
                Label(title, systemImage: systemImage)
                    .font(.headline)
                Spacer()
            }
        }
        .buttonStyle(.bordered)
        .buttonBorderShape(.roundedRectangle(radius: 10))
        .controlSize(.large)
        .tint(AppTheme.brand)
        .disabled(disabled)
    }
}

private enum FeedbackKind: Equatable {
    case info
    case success
    case error

    var color: Color {
        switch self {
        case .info: AppTheme.brand
        case .success: AppTheme.success
        case .error: AppTheme.error
        }
    }

    var icon: String {
        switch self {
        case .info: "info.circle.fill"
        case .success: "checkmark.circle.fill"
        case .error: "exclamationmark.triangle.fill"
        }
    }
}

private struct FeedbackBanner: View {
    let message: String
    let kind: FeedbackKind

    var body: some View {
        Label(message, systemImage: kind.icon)
            .font(.subheadline)
            .foregroundStyle(kind.color)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .background(kind.color.opacity(0.10))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .accessibilityLabel(kind == .error ? "Error: \(message)" : message)
    }
}

private struct ProgressBanner: View {
    let message: String

    var body: some View {
        HStack(spacing: 10) {
            ProgressView()
                .tint(AppTheme.accent)
            Text(message)
                .font(.subheadline)
        }
        .foregroundStyle(AppTheme.brand)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(AppTheme.brand.opacity(0.10))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

private struct RestoringSessionView: View {
    var body: some View {
        ScrollView {
            VStack(spacing: 18) {
                BrandHeader()
                ProgressBanner(message: "Restoring your session…")
            }
            .frame(maxWidth: 620)
            .padding(.horizontal, 20)
            .padding(.vertical, 24)
        }
        .background(AppTheme.background.ignoresSafeArea())
    }
}

private struct ConfigurationErrorView: View {
    let message: String

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                BrandHeader()
                AppCard(title: "Configuration needed") {
                    VStack(alignment: .leading, spacing: 12) {
                        FeedbackBanner(message: message, kind: .error)
                        Label("See ios/README.md for setup steps.", systemImage: "gearshape")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .frame(maxWidth: 620)
            .padding(.horizontal, 20)
            .padding(.vertical, 24)
        }
        .background(AppTheme.background.ignoresSafeArea())
        .tint(AppTheme.brand)
    }
}

private struct KeyboardDismissHandler: UIViewRepresentable {
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeUIView(context: Context) -> WindowTrackingView {
        let view = WindowTrackingView()
        view.isUserInteractionEnabled = false
        view.windowDidChange = { [weak coordinator = context.coordinator] window in
            coordinator?.install(in: window)
        }
        return view
    }

    func updateUIView(_ view: WindowTrackingView, context: Context) {
        context.coordinator.install(in: view.window)
    }

    static func dismantleUIView(_ view: WindowTrackingView, coordinator: Coordinator) {
        view.windowDidChange = nil
        coordinator.install(in: nil)
    }

    final class Coordinator: NSObject, UIGestureRecognizerDelegate {
        private weak var installedWindow: UIWindow?
        private var recognizer: UITapGestureRecognizer?

        func install(in window: UIWindow?) {
            guard installedWindow !== window else { return }
            if let recognizer {
                installedWindow?.removeGestureRecognizer(recognizer)
            }

            installedWindow = window
            recognizer = nil
            guard let window else { return }

            let recognizer = UITapGestureRecognizer(target: self, action: #selector(dismissKeyboard))
            recognizer.cancelsTouchesInView = false
            recognizer.delegate = self
            window.addGestureRecognizer(recognizer)
            self.recognizer = recognizer
        }

        func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
            var touchedView: UIView? = touch.view
            while let view = touchedView {
                if view is UITextView || view is UITextField {
                    return false
                }
                touchedView = view.superview
            }
            return true
        }

        @objc private func dismissKeyboard() {
            installedWindow?.endEditing(true)
        }
    }
}

private final class WindowTrackingView: UIView {
    var windowDidChange: ((UIWindow?) -> Void)?

    override func didMoveToWindow() {
        super.didMoveToWindow()
        windowDidChange?(window)
    }
}

#Preview {
    ContentView(configuration: .failure(.missingValue("SUPABASE_URL")))
}
