-- Local stand-in for the parts of Supabase's `auth` schema that the migrations depend on.
-- Applied by run_tests.sh before the migrations. Never part of db/migrations: on Supabase
-- the real GoTrue schema provides auth.users and auth.uid().
create schema auth;

create table auth.users (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  raw_user_meta_data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

-- Mirrors Supabase: the JWT subject that PostgREST exposes as a transaction-local setting.
create function auth.uid() returns uuid
language sql stable as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid;
$$;

create function auth.role() returns text
language sql stable as $$
  select nullif(current_setting('request.jwt.claim.role', true), '');
$$;

grant usage on schema auth to public;
