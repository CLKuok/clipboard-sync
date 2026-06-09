# Supabase Setup

This guide describes the setup needed before application development starts.

## 1. Create a Supabase Project

1. Sign in to Supabase.
2. Create a new project.
3. Save the project URL and anon public key for future client apps.
4. Do not commit the service-role key.

Future apps should use:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

These values should live in local environment/config files that are not committed.

## 2. Enable Authentication

For the MVP, use email/password authentication.

Checklist:

- Email/password sign-in is enabled.
- Anonymous sign-ins are not used for clipboard access.
- Test users can be created for RLS verification.

## 3. Run the Migration

Apply the initial SQL migration:

```text
supabase/migrations/0001_initial_schema.sql
```

The migration creates:

- `devices`
- `clipboard_items`
- indexes
- row-level security policies
- authenticated role grants

It also enables `pgcrypto` so UUID defaults work through `gen_random_uuid()`.

Expected result:

- The SQL runs without errors on a fresh Supabase project.
- The table editor shows `devices` and `clipboard_items`.
- RLS is enabled for both tables.

## 4. Verify Row-Level Security

Use two test users. See [docs/supabase-verification.md](supabase-verification.md) for a step-by-step manual test script.

Checklist:

- User A can create and read their own device row.
- User A can create and read their own clipboard item.
- User B cannot read User A's rows.
- User B cannot update or delete User A's rows.
- Anonymous requests cannot read or write clipboard data.
- A clipboard item cannot reference another user's device.

## 5. Keep Secrets Out of Git

Do not commit:

- `.env` files.
- Supabase service-role keys.
- Access tokens or refresh tokens.
- Real clipboard contents.

Only the Supabase anon public key should be used by client apps, and authorization should rely on row-level security.
