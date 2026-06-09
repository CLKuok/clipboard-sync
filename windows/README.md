# Windows App

This folder contains the Python Windows CLI for manual Clipboard Sync.

MVP requirements:

- Supabase email/password authentication.
- Manual text push from the Windows clipboard.
- Manual latest-text pull into the Windows clipboard.
- Device registration for the signed-in user.

## Setup

Install `uv`, then run commands from this folder:

```powershell
cd windows
uv sync
Copy-Item .env.example .env
```

Edit `.env` and fill in:

```text
SUPABASE_URL=your-project-url
SUPABASE_ANON_KEY=your-anon-public-key
```

Do not use or store the Supabase service-role key in this app.

## Usage

Login:

```powershell
uv run clipboard-sync-windows login
```

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

## Manual Test Result

The Windows CLI has been tested successfully against the live Supabase project.

Confirmed commands:

- `login`: signed in with Supabase email/password and registered/reused the Windows device.
- `status`: displayed local session and device state.
- `push`: read Windows clipboard text and inserted it into Supabase.
- `pull`: fetched the latest clipboard text from Supabase and copied it to the Windows clipboard.
