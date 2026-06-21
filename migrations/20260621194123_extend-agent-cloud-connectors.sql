alter table public.cluster_pairing_tokens
  add column if not exists provider text not null default 'kubernetes';

alter table public.cluster_pairing_tokens
  drop constraint if exists cluster_pairing_tokens_provider_check;
alter table public.cluster_pairing_tokens
  add constraint cluster_pairing_tokens_provider_check
  check (provider in ('kubernetes', 'gcp'));

alter table public.connected_clusters
  add column if not exists metadata jsonb not null default '{}'::jsonb;

alter table public.connected_clusters
  drop constraint if exists connected_clusters_provider_check;
alter table public.connected_clusters
  add constraint connected_clusters_provider_check
  check (provider in ('kubernetes', 'gcp'));

alter table public.cluster_jobs
  drop constraint if exists cluster_jobs_job_type_check;
alter table public.cluster_jobs
  add constraint cluster_jobs_job_type_check
  check (job_type in ('investigate', 'vulnerability_scan', 'cloud_cost_analysis'));

create index if not exists connected_clusters_user_provider_idx
  on public.connected_clusters(user_id, provider, created_at desc);
