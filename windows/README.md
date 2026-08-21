# Windows App

This folder contains the completed Milestone 3 Python Windows CLI for manual Clipboard Sync. It has also been verified against the Milestone 4 iPhone client.

MVP requirements:

- Supabase email/password authentication.
- Manual text push from the Windows clipboard.
- Manual latest-text pull into the Windows clipboard.
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

## Usage

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

The 24 automated tests do not access the live Supabase project or Windows clipboard. They cover configuration safety, device reuse, session hardening, empty states, failure feedback, and push/pull behavior.

## Manual Test Result

The Windows CLI has been tested successfully against the live Supabase project. On 2026-08-21, Windows↔iPhone manual text sync passed using the same development Auth user.

Confirmed commands:

- `login`: signed in with Supabase email/password and registered/reused the Windows device.
- `status`: displayed local session and device state.
- `push`: read Windows clipboard text and inserted it into Supabase.
- `pull`: fetched the latest clipboard text from Supabase and copied it to the Windows clipboard.

Milestone 5 offline and public/university Wi-Fi live checks are pending.
