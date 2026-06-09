# Clipboard Sync

Clipboard Sync is a simple cross-platform clipboard synchronization project for iPhone and Windows.

The first milestone is intentionally small: text-only clipboard sync, manual push/pull, secure user accounts, and Supabase as the primary synchronization backend. This keeps the MVP reliable on university and public Wi-Fi networks, including networks such as eduroam where direct device-to-device local networking may be blocked.

## MVP Scope

- iPhone app built with SwiftUI.
- Windows app built with Python.
- Supabase backend for authentication and synchronization.
- Text-only clipboard entries.
- Manual sync first: users explicitly push and pull clipboard text.
- Multiple devices per authenticated user.
- Secure per-user data isolation with Supabase row-level security.

Out of scope for the MVP:

- Local network discovery.
- Direct device-to-device sync.
- Bonjour/mDNS.
- WebSocket peer sync.
- Clipboard automation.
- Images, files, rich text, or clipboard history management beyond simple text entries.
- Custom backend services.

## Architecture

The MVP uses Supabase as the primary sync mechanism:

```text
iPhone SwiftUI app  -> Supabase
Windows Python app  -> Supabase
```

Supabase provides:

- Email/password authentication.
- User-scoped database rows.
- Device records.
- Clipboard item storage.
- Row-level security policies.

This design avoids depending on local network behavior, which is often restricted on public and university Wi-Fi.

## Folder Structure

```text
clipboard-sync/
  README.md
  AGENTS.md
  docs/
    architecture.md
    roadmap.md
    supabase-schema.md
  supabase/
    migrations/
    seed.sql
  ios/
    README.md
    ClipboardSync/
  windows/
    README.md
    clipboard_sync/
    tests/
```

## Security Model

- Users authenticate with Supabase Auth.
- Clipboard data is stored per user.
- Row-level security ensures users can only access their own devices and clipboard items.
- Anonymous users must not be able to read or write clipboard data.
- Service-role keys, access tokens, environment files, and real clipboard contents must never be committed.

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for the milestone plan.

## Supabase Schema

See [docs/supabase-schema.md](docs/supabase-schema.md) and [supabase/migrations/0001_initial_schema.sql](supabase/migrations/0001_initial_schema.sql).

## Current Status

The project is in the planning and foundation stage. Documentation, architecture decisions, folder structure, and Supabase schema are being created first. Application code for iOS and Windows has not been written yet.
