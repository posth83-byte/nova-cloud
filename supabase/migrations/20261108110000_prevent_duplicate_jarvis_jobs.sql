-- Prevent duplicate active durable jobs and preserve access tokens when a job is reused.
alter table public.jarvis_jobs
  add column if not exists dedupe_key text,
  add column if not exists access_token_hashes text[] not null default '{}';

update public.jarvis_jobs
set access_token_hashes = array[access_token_hash]
where access_token_hash is not null
  and cardinality(access_token_hashes) = 0;

create unique index if not exists jarvis_jobs_active_dedupe_key_uidx
  on public.jarvis_jobs (dedupe_key)
  where dedupe_key is not null
    and status in ('queued', 'running');

create index if not exists jarvis_jobs_recent_status_updated_idx
  on public.jarvis_jobs (status, updated_at desc);
