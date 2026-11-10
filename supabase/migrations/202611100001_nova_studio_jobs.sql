-- NOVA Studio durable local-GPU production queue
create table if not exists public.nova_studio_jobs (
 id uuid primary key default gen_random_uuid(),
 prompt text not null check (char_length(prompt) between 8 and 2400),
 style text not null default 'cinematic-family-animation',
 aspect text not null default '9:16' check (aspect in ('9:16','16:9','1:1')),
 duration_seconds integer not null default 20 check (duration_seconds between 5 and 180),
 status text not null default 'queued' check (status in ('queued','leased','generating','assembling','uploading','completed','failed')),
 phase text not null default 'Väntar på lokal GPU-arbetare',
 progress integer not null default 0 check (progress between 0 and 100),
 worker_id text, locked_at timestamptz, attempts integer not null default 0,
 max_attempts integer not null default 3, result jsonb, error text,
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 completed_at timestamptz
);
alter table public.nova_studio_jobs add column if not exists scenes jsonb not null default '[]'::jsonb;
create index if not exists nova_studio_jobs_queue_idx on public.nova_studio_jobs(created_at) where status='queued';
alter table public.nova_studio_jobs enable row level security;
revoke all on public.nova_studio_jobs from anon, authenticated;
grant all on public.nova_studio_jobs to service_role;
create or replace function public.claim_nova_studio_job(p_worker_id text)
returns setof public.nova_studio_jobs language sql set search_path=public,pg_temp as $$
 with candidate as (
  select id from public.nova_studio_jobs where status='queued' and attempts<max_attempts
  order by created_at asc for update skip locked limit 1
 )
 update public.nova_studio_jobs j set status='leased',phase='Lokal GPU-arbetare har tagit jobbet',
 progress=2,worker_id=p_worker_id,locked_at=now(),attempts=attempts+1,updated_at=now()
 from candidate c where j.id=c.id returning j.*;
$$;
create or replace function public.recover_stale_nova_studio_jobs(p_stale_seconds integer default 240)
returns integer language plpgsql set search_path=public,pg_temp as $$
declare recovered integer;
begin
 update public.nova_studio_jobs
 set status=case when attempts<max_attempts then 'queued' else 'failed' end,
 phase=case when attempts<max_attempts then 'Återköad efter avbrott' else 'Arbetaren förlorade jobbet efter upprepade försök' end,
 worker_id=null,locked_at=null,
 error=case when attempts<max_attempts then error else coalesce(error,'Arbetarens lease löpte ut') end,
 updated_at=now()
 where status in ('leased','generating','assembling','uploading')
 and locked_at<now()-make_interval(secs=>greatest(60,least(p_stale_seconds,3600)));
 get diagnostics recovered=row_count; return recovered;
end; $$;
revoke all on function public.claim_nova_studio_job(text) from public,anon,authenticated;
revoke all on function public.recover_stale_nova_studio_jobs(integer) from public,anon,authenticated;
grant execute on function public.claim_nova_studio_job(text) to service_role;
grant execute on function public.recover_stale_nova_studio_jobs(integer) to service_role;

create table if not exists public.nova_studio_workers (
 worker_id text primary key,
 status text not null default 'idle' check (status in ('idle','busy')),
 current_job uuid references public.nova_studio_jobs(id) on delete set null,
 last_seen timestamptz not null default now()
);
create index if not exists nova_studio_workers_last_seen_idx on public.nova_studio_workers(last_seen);
alter table public.nova_studio_workers enable row level security;
revoke all on public.nova_studio_workers from anon, authenticated;
grant all on public.nova_studio_workers to service_role;

alter table public.nova_studio_workers add column if not exists planner_mode text not null default 'cloud' check (planner_mode in ('cloud','local'));
