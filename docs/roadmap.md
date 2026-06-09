# Roadmap

## Milestone 1: Project Docs and Structure

Status: in progress.

- Create the planned folder structure.
- Improve `README.md`.
- Add `AGENTS.md`.
- Add architecture, roadmap, and Supabase schema docs.
- Add the initial Supabase migration.
- Do not write iOS or Windows application code yet.

## Milestone 2: Supabase Foundation

- Create a Supabase project.
- Enable email/password authentication.
- Run the initial schema migration.
- Confirm row-level security is enabled.
- Verify one user cannot read or write another user's devices or clipboard items.
- Document required environment variables for future apps.

## Milestone 3: Windows Manual Sync

- Create a beginner-friendly Python app or CLI.
- Add login and logout.
- Register or reuse a Windows device record.
- Add manual push for current clipboard text.
- Add manual pull for the latest synced text.
- Add basic tests for sync behavior.

## Milestone 4: iPhone Manual Sync

- Create a SwiftUI iPhone app.
- Add login and logout.
- Register or reuse an iPhone device record.
- Add manual text push.
- Add manual latest-text pull.
- Display clear success and error states.

## Milestone 5: MVP Hardening

- Handle offline state.
- Handle authentication failures.
- Handle empty clipboard text.
- Handle sync failures.
- Improve setup documentation.
- Test public/university Wi-Fi usage where possible.

## Milestone 6: Future Improvements

- Clipboard automation.
- Supabase realtime subscriptions.
- Better clipboard history UI.
- Optional local sync can be reconsidered later, but it is not part of the first simple MVP.
