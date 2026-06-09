create extension if not exists pgcrypto;

create table public.devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  client_device_key text not null,
  name text not null,
  platform text not null check (platform in ('ios', 'windows')),
  created_at timestamptz not null default now(),
  last_seen_at timestamptz,
  constraint devices_name_not_empty check (length(btrim(name)) > 0),
  constraint devices_client_device_key_not_empty check (length(btrim(client_device_key)) > 0),
  constraint devices_user_client_device_key_unique unique (user_id, client_device_key),
  constraint devices_id_user_id_unique unique (id, user_id)
);

create table public.clipboard_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  source_device_id uuid,
  content text not null,
  content_type text not null default 'text/plain',
  created_at timestamptz not null default now(),
  constraint clipboard_items_content_not_empty check (length(content) > 0),
  constraint clipboard_items_content_type_text_only check (content_type = 'text/plain'),
  constraint clipboard_items_source_device_user_fk
    foreign key (source_device_id, user_id)
    references public.devices(id, user_id)
    on delete restrict
);

create index devices_user_idx
  on public.devices(user_id);

create index clipboard_items_user_created_idx
  on public.clipboard_items(user_id, created_at desc);

alter table public.devices enable row level security;
alter table public.clipboard_items enable row level security;

revoke all on table public.devices from anon;
revoke all on table public.clipboard_items from anon;

grant select, insert, update, delete on table public.devices to authenticated;
grant select, insert, update, delete on table public.clipboard_items to authenticated;

create policy "Users can read their devices"
on public.devices
for select
to authenticated
using (auth.uid() = user_id);

create policy "Users can insert their devices"
on public.devices
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "Users can update their devices"
on public.devices
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can delete their devices"
on public.devices
for delete
to authenticated
using (auth.uid() = user_id);

create policy "Users can read their clipboard items"
on public.clipboard_items
for select
to authenticated
using (auth.uid() = user_id);

create policy "Users can insert their clipboard items"
on public.clipboard_items
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "Users can update their clipboard items"
on public.clipboard_items
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can delete their clipboard items"
on public.clipboard_items
for delete
to authenticated
using (auth.uid() = user_id);
