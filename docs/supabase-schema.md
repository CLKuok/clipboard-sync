# Supabase Schema

Supabase Auth is the source of user identity. Application tables reference `auth.users(id)` through a `user_id` column.

## Tables

### `devices`

Tracks devices owned by each authenticated user.

Columns:

- `id`: device ID.
- `user_id`: owner, referencing `auth.users(id)`.
- `name`: user-visible device name.
- `platform`: `ios` or `windows`.
- `created_at`: creation timestamp.
- `last_seen_at`: optional last activity timestamp.

### `clipboard_items`

Stores text clipboard entries owned by each authenticated user.

Columns:

- `id`: clipboard item ID.
- `user_id`: owner, referencing `auth.users(id)`.
- `source_device_id`: optional device that created the item.
- `content`: clipboard text.
- `content_type`: defaults to `text/plain`.
- `created_at`: creation timestamp.

## Initial Migration

The SQL migration lives at:

```text
supabase/migrations/0001_initial_schema.sql
```

## Security

Row-level security must be enabled for both tables.

Policy requirements:

- Authenticated users can manage their own device rows.
- Authenticated users can manage their own clipboard item rows.
- Users cannot access rows owned by other users.
- Anonymous users cannot access clipboard data.

## Verification Checklist

- Create two test users.
- Insert a device and clipboard item as user A.
- Confirm user A can read both rows.
- Confirm user B cannot read user A's rows.
- Confirm anonymous requests cannot read or write clipboard data.
