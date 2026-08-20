# iPhone App

`ClipboardSync/ClipboardSync.xcodeproj` is the iPhone-only SwiftUI client for Milestone 4. It uses Supabase Swift for email/password authentication and manual text synchronization.

The app can:

- restore a saved Supabase session;
- sign in and log out;
- keep one stable `client_device_key` for this app installation;
- register or recover its iOS device row;
- push text entered or pasted into the app;
- pull and display the latest synced text;
- show loading, empty, success, configuration, and error states.

It does not monitor or change the iPhone clipboard automatically.

## First-time configuration

The project contains safe placeholder values so it builds without secrets. A real Supabase connection uses an ignored local file.

1. In Terminal, move to the repository:

   ```bash
   cd /Users/andykuok/Documents/Project/clipboard-sync
   ```

2. Create the ignored local configuration from the example:

   ```bash
   cp ios/ClipboardSync/Config/Supabase.example.xcconfig ios/ClipboardSync/Config/Supabase.xcconfig
   ```

3. Open `ios/ClipboardSync/Config/Supabase.xcconfig` in VS Code. Replace only the two placeholder values:

   ```text
   SUPABASE_URL = https:/$()/your-project-ref.supabase.co
   SUPABASE_ANON_KEY = your-publishable-or-anon-key
   ```

   Keep `$()` between the URL slashes; `.xcconfig` files otherwise interpret `//` as a comment. Use the project base URL and the publishable or legacy anon key. Never use a secret or service-role key.

4. Confirm Git ignores the local file:

   ```bash
   git status --short
   git check-ignore ios/ClipboardSync/Config/Supabase.xcconfig
   ```

The second command should print the local file path, and `git status` must not list that file.

## Run in Xcode

1. Open `ios/ClipboardSync/ClipboardSync.xcodeproj` in Xcode.
2. Let Xcode finish resolving package dependencies. The exact resolved versions are recorded in `Package.resolved`.
3. At the top of the Xcode window, select the `ClipboardSync` scheme and an iPhone simulator such as iPhone 17 Pro.
4. Press `Command-R` to build and run.
5. Sign in with an existing email/password user from the same Supabase project as the Windows client.

If the app shows “Configuration needed,” check the local `.xcconfig` filename and its two values, then use **Product → Clean Build Folder** and run again.

## Run tests

In Xcode, press `Command-U`. From Terminal, the equivalent command for the installed simulator is:

```bash
xcodebuild -project ios/ClipboardSync/ClipboardSync.xcodeproj \
  -scheme ClipboardSync \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' \
  test
```

The tests use a mocked sync service. They require no Supabase credentials and do not contact the live project.

## Live acceptance checklist

Use synthetic text rather than personal clipboard content.

1. Sign in on the simulator and confirm the manual sync screen appears.
2. Quit and reopen the app; confirm the session is restored.
3. Log out; confirm the sign-in screen returns. Sign in again and confirm the same logical iOS device row is reused.
4. Push synthetic text from Windows, then use **Pull Latest** on iPhone and confirm it appears.
5. Push different synthetic text from iPhone, then pull on Windows and confirm it reaches the Windows clipboard.
6. In the Supabase Table Editor, confirm the authenticated user's iOS device row and both clipboard rows exist.
7. Delete only the test iOS device row in Supabase, push again from iPhone, and confirm the row is recreated with the same `client_device_key` and the push succeeds.
8. Confirm logout, empty text, and an intentionally offline request show understandable states.

## Run on a physical iPhone

Do this after the simulator checks pass:

1. In Xcode, open **Xcode → Settings → Accounts** and add your Apple ID.
2. Select the ClipboardSync project, then the ClipboardSync target, then **Signing & Capabilities**.
3. Enable automatic signing and select your Personal Team.
4. Connect and trust the iPhone, select it as the run destination, and press `Command-R`.
5. If prompted, enable Developer Mode on the iPhone and follow Xcode's instructions.

App Store distribution is outside this milestone.

## Verification record

- 2026-07-24: blank SwiftUI baseline built and its generated test passed on iPhone 17 Pro/iOS 26.5 simulator.
- 2026-07-24: Supabase-enabled app built, launched to its safe missing-configuration state, and all 17 mocked tests passed on the same simulator.
- 2026-08-21: live Supabase authentication, readable authentication errors, session restoration, logout, iOS device-row reuse, empty states, and Windows↔iPhone manual text sync passed using a development Auth user.
- Optional follow-up checks: live deleted-device recovery and deployment to a physical iPhone.
