# Windows App

This folder contains the Python Windows clients for manual Clipboard Sync. Milestone 6 adds a small desktop interface while retaining the completed and verified command-line interface.

MVP requirements:

- Supabase email/password authentication.
- Manual text push from the desktop input or, when using the CLI, the Windows clipboard.
- Manual latest-text pull with a separate copy-to-clipboard action in the GUI.
- Device registration for the signed-in user.

## Setup

Requirements:

- Windows with clipboard access.
- Python 3.11 or later.
- [`uv`](https://docs.astral.sh/uv/).

From the repository root, run:

```powershell
cd windows
uv sync
Copy-Item .env.example .env
```

Edit `.env` and fill in:

```text
SUPABASE_URL=your-project-url
SUPABASE_ANON_KEY=your-publishable-or-anon-key
```

Use the project URL and publishable or legacy anon key from the same Supabase project as the iPhone app. Do not use or store a secret or service-role key in this app.

## Desktop app

After setup, launch the graphical Windows app:

```powershell
uv run clipboard-sync-windows-gui
```

Sign in with the same Supabase Auth user as the iPhone app. The window uses the same rounded, grouped Push/Pull layout as the iPhone client. It can push text entered or pasted into the app, pull and display the latest synced text, restore the saved session after reopening, and log out. Expected offline and authentication failures appear as compact in-app feedback rather than tracebacks.

The interface supports keyboard navigation and Enter-to-sign-in. Type or paste text into **Push**, then select **Push Text**. If the box is empty, that same explicit action reads and uploads the current Windows clipboard, then shows the uploaded text in the box. **Pull Latest** only displays the newest synced text; select **Copy to Clipboard** when you want to place it on the Windows clipboard. The copy button remains disabled until text has been pulled. The app does not monitor the clipboard in the background and clears both text areas when the user logs out.

This is the first Milestone 6 desktop version. It runs through `uv`; packaging it as a standalone installer is not part of this initial UI slice.

## Command-line usage

Login:

```powershell
uv run clipboard-sync-windows login --email "your-test-email@example.com"
```

The password is entered at a hidden prompt. Use the same Supabase Auth user on Windows and iPhone for cross-device sync.

Check local session/device state:

```powershell
uv run clipboard-sync-windows status
```

Push current Windows clipboard text to Supabase:

```powershell
uv run clipboard-sync-windows push
```

Pull latest Supabase clipboard text and copy it to Windows clipboard:

```powershell
uv run clipboard-sync-windows pull
```

Logout and remove local session tokens:

```powershell
uv run clipboard-sync-windows logout
```

## Local State

The CLI stores session tokens, the reusable `client_device_key`, and the Supabase `device_id` in the current user's app data folder. These values are local machine state and must not be committed.

If a saved session is no longer valid, the CLI asks you to log in again and clears only the invalid account/session data. The stable installation device key is preserved.

## Empty and failure states

- An empty or whitespace-only clipboard is rejected without contacting Supabase.
- If no synced row exists, `pull` reports `No synced text yet` and leaves the Windows clipboard unchanged.
- Offline, invalid-login, expired-session, and sync failures produce one readable `Error:` line instead of a traceback.
- After an offline or temporary sync failure, reconnect and run the same command again.

## Run tests

From the `windows` folder:

```powershell
uv run pytest -q
```

The 34 automated tests do not access the live Supabase project or Windows clipboard. They cover configuration safety, device reuse, session hardening, empty states, failure feedback, desktop-controller behavior, presentation constants, entered-text behavior, and push/pull behavior.

## Manual Test Result

The Windows CLI has been tested successfully against the live Supabase project. On 2026-08-21, Windows↔iPhone manual text sync passed using the same development Auth user.

Confirmed commands:

- `login`: signed in with Supabase email/password and registered/reused the Windows device.
- `status`: displayed local session and device state.
- `push`: read Windows clipboard text and inserted it into Supabase.
- `pull`: fetched the latest clipboard text from Supabase and copied it to the Windows clipboard.

Milestone 5 offline feedback passed live Windows testing on 2026-08-21. Public/university Wi-Fi remains an explicitly deferred, non-blocking follow-up.

The Milestone 6 GUI was smoke-tested on Windows on 2026-08-21: the sign-in and signed-in layouts rendered at the intended size and the shared app icon loaded successfully.
