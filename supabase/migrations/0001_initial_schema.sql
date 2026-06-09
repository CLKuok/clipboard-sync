create extension if not exists pgcrypto;

create table public.devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  platform text not null check (platform in ('ios', 'windows')),
  created_at timestamptz not null default now(),
  last_seen_at timestamptz
);

create table public.clipboard_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  source_device_id uuid references public.devices(id) on delete set null,
  content text not null,
  content_type text not null default 'text/plain',
  created_at timestamptz not null default now()
);

create index devices_user_idx
  on public.devices(user_id);

create index clipboard_items_user_created_idx
  on public.clipboard_items(user_id, created_at desc);

alter table public.devices enable row level security;
alter table public.clipboard_items enable row level security;

create policy "Users can manage their devices"
on public.devices
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can manage their clipboard items"
on public.clipboard_items
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
