# AGENTS.md

This file defines the project rules and architecture decisions for AI agents and contributors working on Clipboard Sync.

## Project Direction

- Keep the MVP simple, reliable, and beginner-friendly.
- Use Supabase as the primary synchronization mechanism for the MVP.
- Build an iPhone app with SwiftUI.
- Build a Windows app with Python.
- Keep clipboard sync text-only for now.
- Start with manual push and pull actions.
- Support multiple devices per authenticated user.

## MVP Boundaries

- Do not add local network discovery in the MVP.
- Do not require direct device-to-device connections.
- Do not add Bonjour, mDNS, LAN sockets, or peer WebSocket sync in the MVP.
- Do not add clipboard automation yet.
- Do not add image, file, rich text, or binary clipboard sync yet.
- Do not create a custom backend unless Supabase cannot satisfy a requirement.
- Do not write application code until the current docs/schema milestone is complete.

## Architecture Decisions

- Supabase Auth is the identity provider for the MVP.
- Supabase Postgres stores devices and clipboard text entries.
- Supabase row-level security protects all user-owned data.
- The cloud database is the source of truth for manual sync.
- Clipboard history is scoped to one authenticated user account.
- Devices belong to users through the `devices` table.

## Security Rules

- Require authentication for clipboard access.
- Enforce per-user data isolation with row-level security.
- Do not allow anonymous clipboard reads or writes.
- Never commit Supabase service-role keys.
- Never commit access tokens, refresh tokens, `.env` files, or real clipboard contents.
- Use anon/public client keys only in client apps, and rely on RLS for authorization.

## Documentation Rules

- Keep documentation clear enough for a beginner to follow.
- Prefer small milestones over broad rewrites.
- Record major architecture decisions in `docs/architecture.md`.
- Keep Supabase schema details in `docs/supabase-schema.md`.
- Keep roadmap status in `docs/roadmap.md`.
