# Architecture

Clipboard Sync starts with the simplest reliable architecture: both clients synchronize through Supabase.

## Goals

- Work on university and public Wi-Fi.
- Avoid local networking requirements for the MVP.
- Keep the implementation understandable for beginners.
- Support iPhone and Windows clients.
- Protect clipboard data with authentication and per-user authorization.

## MVP Sync Flow

```text
iPhone SwiftUI app  -> Supabase Auth + Database
Windows Python app  -> Supabase Auth + Database
```

Manual push:

1. User signs in.
2. Device creates or reuses a device record.
3. User chooses to push text.
4. App inserts a row into `clipboard_items`.

Manual pull:

1. User signs in.
2. App fetches the latest `clipboard_items` row for the user.
3. App displays or copies the text locally.

## Why Supabase First

Public and university Wi-Fi networks often block direct device-to-device communication. A cloud sync path avoids relying on local network discovery, open inbound ports, multicast DNS, or peer reachability.

Supabase is a practical first backend because it provides:

- Authentication.
- Postgres storage.
- Row-level security.
- Hosted infrastructure.
- Optional realtime features for later milestones.

## Data Ownership

Supabase Auth owns user identity. Application tables store `user_id` values referencing `auth.users(id)`.

Every device and clipboard item belongs to exactly one user. Row-level security policies enforce that users only access their own rows.

## Device Identity and Reuse

Each installed client should create one local device identity and reuse it for future syncs.

Recommended MVP behavior:

- On first successful sign-in, the app creates a `devices` row for that user.
- The app stores the returned `devices.id` locally.
- Future launches reuse that stored device ID instead of creating a new row.
- If the stored device ID no longer exists in Supabase, the app creates a new device row and stores the new ID.
- Device names should be user-readable, such as `John's iPhone` or `Windows Laptop`.
- Device records are not authentication credentials; user sign-in remains the source of trust.

This avoids duplicate device rows while keeping the MVP simple.

## Explicit Non-Goals for MVP

- Local discovery.
- Direct device-to-device sync.
- Bonjour/mDNS.
- Peer WebSocket sync.
- Clipboard automation.
- Image/file/rich-text clipboard sync.
- Custom backend services.

These can be reconsidered after the manual text-only cloud MVP is stable.
