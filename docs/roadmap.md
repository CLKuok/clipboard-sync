# Roadmap

## Milestone 1: Project Docs and Structure

Status: accepted.

- Create the planned folder structure.
- Improve `README.md`.
- Add `AGENTS.md`.
- Add architecture, roadmap, and Supabase schema docs.
- Add the initial Supabase migration.
- Do not write iOS or Windows application code yet.

Acceptance criteria:

- The repository has the agreed `docs/`, `supabase/`, `ios/`, and `windows/` folders.
- `README.md` explains the MVP scope, architecture, roadmap, and security model.
- `AGENTS.md` records the project rules without blocking future milestone work.
- `docs/architecture.md` explains the Supabase-first architecture and device reuse strategy.
- `docs/roadmap.md` has milestone acceptance criteria.
- `docs/supabase-schema.md` and `docs/supabase-setup.md` explain the database and setup process.
- `supabase/migrations/0001_initial_schema.sql` contains the initial schema and RLS policies.
- No iOS or Windows application code has been added.

## Milestone 2: Supabase Foundation

Status: in progress.

- Create a Supabase project.
- Enable email/password authentication.
- Run the initial schema migration.
- Confirm row-level security is enabled.
- Verify one user cannot read or write another user's devices or clipboard items.
- Document required environment variables for future apps.

Acceptance criteria:

- A Supabase project exists for development.
- Email/password authentication is enabled.
- The initial migration runs successfully.
- RLS is enabled on `devices` and `clipboard_items`.
- Two test users have been used to verify per-user data isolation.
- Anonymous requests cannot read or write clipboard data.
- Devices can be registered and associated with their owning users.
- Clipboard items can be inserted and queried by the owning user.
- Clipboard items cannot reference another user's device as their source device.
- Future client apps know which public environment values they need.

## Milestone 3: Windows Manual Sync

- Create a beginner-friendly Python app or CLI.
- Add login and logout.
- Register or reuse a Windows device record.
- Add manual push for current clipboard text.
- Add manual pull for the latest synced text.
- Add basic tests for sync behavior.

Acceptance criteria:

- A Windows user can sign in and sign out.
- The app registers one reusable Windows device record per local app install.
- Manual push uploads text from the Windows clipboard.
- Manual pull copies the latest synced text into the Windows clipboard.
- Empty clipboard and sync failure states are handled clearly.
- Basic Python tests cover device reuse and push/pull behavior.

## Milestone 4: iPhone Manual Sync

- Create a SwiftUI iPhone app.
- Add login and logout.
- Register or reuse an iPhone device record.
- Add manual text push.
- Add manual latest-text pull.
- Display clear success and error states.

Acceptance criteria:

- An iPhone user can sign in and sign out.
- The app registers one reusable iPhone device record per local app install.
- Manual push uploads text entered or pasted by the user.
- Manual pull displays the latest synced text.
- Auth, empty text, and sync failure states are visible to the user.

## Milestone 5: MVP Hardening

- Handle offline state.
- Handle authentication failures.
- Handle empty clipboard text.
- Handle sync failures.
- Improve setup documentation.
- Test public/university Wi-Fi usage where possible.

Acceptance criteria:

- The MVP gives understandable feedback when offline or unauthenticated.
- Public/university Wi-Fi usage has been tested where possible.
- Setup docs are complete enough for a beginner to recreate the project.
- No secrets, tokens, or real clipboard contents are committed.

## Milestone 6: Future Improvements

- Clipboard automation.
- Supabase realtime subscriptions.
- Better clipboard history UI.
- Optional local sync can be reconsidered later, but it is not part of the first simple MVP.

Acceptance criteria:

- Future improvements are only started after the manual text-only MVP works reliably.
- Automation or realtime changes do not break the manual sync path.
