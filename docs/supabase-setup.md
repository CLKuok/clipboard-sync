# Supabase Setup

This guide recreates the development backend and connects both Clipboard Sync clients. Use synthetic test text and a dedicated Supabase Auth user.

## 1. Create the project

1. Sign in to the [Supabase Dashboard](https://supabase.com/dashboard).
2. Create a project and wait until provisioning finishes.
3. Open the project's **Connect** dialog. Copy:
   - the base project URL, shaped like `https://your-project-ref.supabase.co`;
   - a publishable key, shaped like `sb_publishable_...`.
4. If the Connect dialog is unavailable, use **Project Settings → API Keys** for the publishable key and **Project Settings → Data API** for the project URL.

A legacy `anon` key also works, but new client configuration should prefer the publishable key. Never use an `sb_secret_...` or legacy `service_role` key. Supabase's [API key guide](https://supabase.com/docs/guides/getting-started/api-keys) explains the difference.

## 2. Enable email/password authentication

Email authentication is normally enabled by default. Verify it in **Authentication → Sign In / Providers → Email**.

For development, open **Authentication → Users**, select **Add user**, and create a dedicated test user. This is an app user; it is separate from the account used to sign in to the Supabase Dashboard. Use the same app user's email and password on Windows and iPhone.

If email confirmation is enabled, confirm the address before testing. See Supabase's [password authentication guide](https://supabase.com/docs/guides/auth/passwords) for current behavior.

## 3. Apply the existing schema

Do not design tables manually in Table Editor.

1. Open `supabase/migrations/0001_initial_schema.sql` from this repository and copy all of it.
2. In Supabase, open **SQL Editor → New query**.
3. Paste the migration and select **Run**.
4. Open **Table Editor** and confirm `devices` and `clipboard_items` exist.
5. Confirm RLS is enabled for both tables.

The migration also enables `pgcrypto`, creates the required indexes and authenticated-role grants, and installs the user-isolation policies.

## 4. Configure Windows

In Windows PowerShell from the repository root:

```powershell
Set-Location windows
uv sync
Copy-Item .env.example .env
```

Edit the ignored `windows/.env` file:

```text
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=sb_publishable_your-key
```

Then verify login:

```powershell
uv run clipboard-sync-windows login --email "your-test-email@example.com"
uv run clipboard-sync-windows status
```

Enter the app user's password at the hidden prompt. A successful status shows `Logged in: yes`, a device ID, and `Client device key: set`. Continue with the full [Windows guide](../windows/README.md).

## 5. Configure iPhone

On the Mac, from the repository root:

```bash
cp ios/ClipboardSync/Config/Supabase.example.xcconfig ios/ClipboardSync/Config/Supabase.xcconfig
```

Edit the ignored `Supabase.xcconfig`:

```text
SUPABASE_URL = https:/$()/your-project-ref.supabase.co
SUPABASE_ANON_KEY = sb_publishable_your-key
```

The `$()` is required so Xcode does not treat `//` as a comment. Open `ios/ClipboardSync/ClipboardSync.xcodeproj`, select the `ClipboardSync` scheme and an iPhone destination, then run the app and sign in as the same test user. Continue with the full [iPhone guide](../ios/README.md).

## 6. Verify security and sync

Run the complete two-user RLS script in [supabase-verification.md](supabase-verification.md). Its expected results include:

- each user can access only their own devices and clipboard items;
- anonymous requests cannot read or write application data;
- a clipboard item cannot reference another user's device.

For client verification, push synthetic text from one platform and pull it on the other. Both clients must use the same Supabase project and Auth user.

## Troubleshooting

- **Configuration error:** use only the HTTPS base URL with no `/rest/v1` suffix, query, or fragment.
- **Key rejected:** use a publishable or legacy anon key. The clients intentionally reject secret and service-role keys.
- **Incorrect email or password:** use the app user listed under **Authentication → Users**, not the Supabase Dashboard account unless they happen to be the same.
- **Session expired:** sign in again. Windows removes invalid local session tokens while retaining its installation device key.
- **Offline message:** reconnect, complete any public-Wi-Fi captive portal, then retry the same manual action. Draft iPhone text is retained after a retryable failure.
- **No synced text yet:** no clipboard row exists for this user; this is an empty state and does not modify the Windows clipboard.
- **RLS or device error:** confirm the migration ran once in the intended project and both clients use that project's URL and key.

## Keep local values out of Git

Never commit:

- `.env` or `Supabase.xcconfig` files;
- secret or service-role keys;
- access or refresh tokens;
- real clipboard contents.

Before publishing changes, inspect `git status` and the staged diff. Client authorization must continue to rely on Supabase Auth and RLS.
