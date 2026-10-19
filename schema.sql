-- Run once in your Supabase project's SQL Editor.
create table public.events (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(trim(name)) between 1 and 150),
  event_date date not null,
  location text not null check (char_length(trim(location)) between 1 and 200),
  created_at timestamptz not null default now()
);

create table public.attendance (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  student_name text not null check (char_length(trim(student_name)) between 1 and 150),
  student_id text not null check (char_length(trim(student_id)) between 1 and 80),
  status text not null default 'absent' check (status in ('present', 'absent')),
  created_at timestamptz not null default now(),
  unique (event_id, student_id)
);
create index events_date_idx on public.events(event_date desc);
-- The unique constraint already indexes attendance by event_id.

alter table public.events enable row level security;
alter table public.attendance enable row level security;
-- No public policies: only the Flask server's privileged key can access data.
revoke all on public.events, public.attendance from anon, authenticated;
grant all on public.events, public.attendance to service_role;
