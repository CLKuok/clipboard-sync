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

Status: complete.

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

Status: complete.

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

Status: complete.

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

Verification completed:

- The app and its mocked unit tests build and run on the iPhone 17 Pro/iOS 26.5 simulator.
- Live Supabase email/password authentication, session restoration, logout, iOS device-row reuse, empty states, and manual Windows-to-iPhone and iPhone-to-Windows text sync were verified on 2026-08-21.
- Physical-iPhone deployment remains an optional non-blocking check.

## Milestone 5: MVP Hardening

Status: complete.

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

Automated verification completed:

- Windows configuration, authentication, offline, empty-text, empty-pull, sync-failure, device, and push/pull tests pass.
- The iOS app builds and its authentication, offline, empty-state, device, and push/pull tests pass on iPhone 17 Pro/iOS 26.5 simulator.
- No schema or authentication-model change was required.

Live verification completed:

- Friendly offline feedback was confirmed on a physical iPhone and the Windows CLI on 2026-08-21.
- Public/university Wi-Fi testing is explicitly deferred until a suitable network is available; this is non-blocking under the "where possible" acceptance criterion.

## Milestone 6: Desktop and App Presentation

Status: implementation complete; iOS build and cross-platform visual verification pending.

- Add a simple Windows desktop interface while keeping the working CLI available.
- Reuse the hardened authentication, device registration, and manual push/pull services.
- Add an original iOS app icon and include it in the Xcode asset catalog.
- Keep synchronization manual and text-only during this UI improvement.

Acceptance criteria:

- The Windows desktop interface can sign in, restore a session, push the current clipboard, pull the latest text, log out, and show useful progress/error states.
- The Windows CLI remains available and compatible with the iPhone client.
- The iPhone app builds with its own app icon.
- Existing Windows and iOS automated checks continue to pass.
- No automatic clipboard monitoring, realtime subscriptions, history browser, schema change, or binary content is added.

Later improvements such as automation, realtime updates, richer history, or optional local sync remain outside this milestone.

Implementation completed:

- Windows and iPhone now use one icon-led blue/cyan presentation with matching headers, grouped Push/Pull sections, account context, and inline progress/success/error feedback.
- Both GUIs accept manually entered or pasted text and fall back to reading text from the system clipboard only after an explicit push with an empty box; the unchanged Windows CLI continues to push the current clipboard through the same sync services.
- The iPhone app keeps its editable push text and selectable pulled text while using the same presentation hierarchy.
- All 34 Windows automated tests pass, and a Windows GUI smoke check confirms both screens render with the expected controls and window icon.

Remaining acceptance verification:

- Build and run the refreshed iPhone app and its mocked tests in Xcode.
- Visually compare both clients and perform one synthetic sync in each direction before changing this milestone to complete.
