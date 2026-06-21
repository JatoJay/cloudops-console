create extension if not exists pgcrypto;

create table if not exists public.cluster_pairing_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  token_hash text not null unique,
  cluster_name text not null check (char_length(cluster_name) between 1 and 120),
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.connected_clusters (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 120),
  provider text not null default 'kubernetes',
  status text not null default 'offline' check (status in ('offline', 'online', 'revoked')),
  agent_secret_hash text not null unique,
  last_seen timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.cluster_jobs (
  id uuid primary key default gen_random_uuid(),
  cluster_id uuid not null references public.connected_clusters(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  job_type text not null check (job_type in ('investigate', 'vulnerability_scan')),
  status text not null default 'queued' check (status in ('queued', 'running', 'completed', 'failed')),
  payload jsonb not null default '{}'::jsonb,
  progress jsonb not null default '[]'::jsonb,
  result jsonb,
  error text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  updated_at timestamptz not null default now()
);

create index if not exists cluster_pairing_tokens_user_id_idx on public.cluster_pairing_tokens(user_id, created_at desc);
create index if not exists connected_clusters_user_id_idx on public.connected_clusters(user_id, created_at desc);
create index if not exists cluster_jobs_user_id_idx on public.cluster_jobs(user_id, created_at desc);
create index if not exists cluster_jobs_dispatch_idx on public.cluster_jobs(cluster_id, status, created_at);

alter table public.cluster_pairing_tokens enable row level security;
alter table public.connected_clusters enable row level security;
alter table public.cluster_jobs enable row level security;

create or replace function public.owns_connected_cluster(target_cluster_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.connected_clusters
    where id = target_cluster_id and user_id = auth.uid() and status <> 'revoked'
  );
$$;

revoke all on function public.owns_connected_cluster(uuid) from public;
grant execute on function public.owns_connected_cluster(uuid) to authenticated;

drop policy if exists pairing_tokens_select_own on public.cluster_pairing_tokens;
create policy pairing_tokens_select_own on public.cluster_pairing_tokens for select
  to authenticated using (user_id = auth.uid());
drop policy if exists pairing_tokens_insert_own on public.cluster_pairing_tokens;
create policy pairing_tokens_insert_own on public.cluster_pairing_tokens for insert
  to authenticated with check (user_id = auth.uid() and used_at is null);

drop policy if exists connected_clusters_select_own on public.connected_clusters;
create policy connected_clusters_select_own on public.connected_clusters for select
  to authenticated using (user_id = auth.uid());
drop policy if exists connected_clusters_delete_own on public.connected_clusters;
create policy connected_clusters_delete_own on public.connected_clusters for delete
  to authenticated using (user_id = auth.uid());

drop policy if exists cluster_jobs_select_own on public.cluster_jobs;
create policy cluster_jobs_select_own on public.cluster_jobs for select
  to authenticated using (user_id = auth.uid());
drop policy if exists cluster_jobs_insert_own on public.cluster_jobs;
create policy cluster_jobs_insert_own on public.cluster_jobs for insert
  to authenticated with check (
    user_id = auth.uid() and public.owns_connected_cluster(cluster_id)
  );

grant select, insert on public.cluster_pairing_tokens to authenticated;
grant select, delete on public.connected_clusters to authenticated;
grant select, insert on public.cluster_jobs to authenticated;
