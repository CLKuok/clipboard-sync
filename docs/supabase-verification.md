# Supabase Manual Verification

Use this checklist after creating a fresh Supabase project and running `supabase/migrations/0001_initial_schema.sql`.

The goal is to prove:

- Devices can be registered for a signed-in user.
- Clipboard items can be inserted and queried by their owner.
- User A cannot access User B's clipboard rows.
- Anonymous requests cannot access clipboard data.

## Prerequisites

- A Supabase project with the initial migration applied.
- Email/password authentication enabled.
- Two test users, called User A and User B.
- The project URL and anon public key.
- Access tokens for User A and User B.

You can obtain user access tokens by signing in through Supabase's API, SDK examples, or dashboard API tools. Do not commit those tokens.

## 1. Anonymous Access Should Fail

Using only the anon public key and no signed-in user token:

- Query `devices`.
- Query `clipboard_items`.
- Try to insert a `devices` row.
- Try to insert a `clipboard_items` row.

Expected result:

- Reads return no private rows.
- Inserts fail because `auth.uid()` is null and the RLS `with check` condition is not satisfied.

## 2. Register a Device for User A

As User A, insert a device:

```json
{
  "client_device_key": "user-a-windows-dev",
  "name": "User A Windows",
  "platform": "windows"
}
```

Expected result:

- Insert succeeds.
- The response includes a device `id`.
- Reusing the same `client_device_key` for User A should update/reuse the same logical device in client code, not create endless duplicates.

## 3. Register a Device for User B

As User B, insert a device:

```json
{
  "client_device_key": "user-b-iphone-dev",
  "name": "User B iPhone",
  "platform": "ios"
}
```

Expected result:

- Insert succeeds.
- User B gets a different device `id`.

## 4. Insert Clipboard Text for User A

As User A, insert a clipboard item:

```json
{
  "source_device_id": "<user-a-device-id>",
  "content": "hello from user a",
  "content_type": "text/plain"
}
```

Expected result:

- Insert succeeds.
- User A can query the row ordered by `created_at desc`.

## 5. User B Cannot Read User A's Clipboard

As User B:

- Query `clipboard_items`.
- Filter by User A's clipboard item ID.
- Try to update User A's clipboard item.
- Try to delete User A's clipboard item.

Expected result:

- User B cannot see User A's row.
- Update and delete affect no rows or are rejected by RLS.

## 6. Cross-User Device References Should Fail

As User A, try to insert a clipboard item using User B's device ID:

```json
{
  "source_device_id": "<user-b-device-id>",
  "content": "bad source device",
  "content_type": "text/plain"
}
```

Expected result:

- Insert fails because `(source_device_id, user_id)` must reference a device owned by the same user.

## 7. Text-Only Constraints Should Hold

Try these invalid inserts as an authenticated user:

- Empty `content`.
- `content_type` other than `text/plain`.
- Empty `name` for a device.
- `platform` other than `ios` or `windows`.

Expected result:

- Each insert fails with a constraint error.

## Completion Criteria

Milestone 2 is ready when all expected results above are confirmed on a fresh Supabase project.
