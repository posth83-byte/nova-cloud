-- Atomically deduplicate jobs and preserve every polling access token.
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

-- Serialize all enqueue operations in this table. Matching and token updates
-- occur inside the same transaction, eliminating the previous race window.
create or replace function public.jarvis_enqueue_job(
  p_task text,
  p_dedupe_key text,
  p_token_hash text,
  p_history jsonb default '[]'::jsonb,
  p_push_subscription jsonb default null
)
returns jsonb
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
  v_existing public.jarvis_jobs%rowtype;
  v_tokens text[];
  v_task_tokens text[];
  v_candidate_tokens text[];
  v_task_numbers text[];
  v_candidate_numbers text[];
  v_overlap integer;
  v_task_negated boolean;
  v_candidate_negated boolean;
  v_match boolean := false;
  v_status text;
begin
  if nullif(btrim(p_task), '') is null or nullif(p_dedupe_key, '') is null
     or nullif(p_token_hash, '') is null then
    raise exception 'Task, dedupe key and token hash are required';
  end if;

  -- One transaction-level lock serializes enqueue operations for this queue.
  perform pg_advisory_xact_lock(731942018);

  select * into v_existing
  from public.jarvis_jobs j
  where j.status in ('queued', 'running', 'completed', 'failed')
    and (j.status in ('queued', 'running') or j.updated_at >= now() - interval '30 days')
    and j.dedupe_key = p_dedupe_key
  order by j.updated_at desc
  limit 1
  for update;

  if not found then
    select coalesce(array_agg(distinct t order by t), '{}')
      into v_task_tokens
    from unnest(regexp_split_to_array(
      regexp_replace(lower(coalesce(p_task, '')), '[^[:alnum:]_ ]', ' ', 'g'),
      '[[:space:]]+'
    )) t
    where t <> '';

    select coalesce(array_agg(t order by t), '{}')
      into v_task_numbers
    from unnest(v_task_tokens) t
    where t ~ '^[0-9]+([.,][0-9]+)?$';

    v_task_negated := v_task_tokens && array[
      'inte','ej','aldrig','inget','ingen','ingenting','utan',
      'not','never','no','without','stoppa','avbryt'
    ];

    if cardinality(v_task_tokens) >= 6 then
      for v_existing in
        select j.*
        from public.jarvis_jobs j
        where j.status in ('queued', 'running', 'completed', 'failed')
          and (j.status in ('queued', 'running') or j.updated_at >= now() - interval '30 days')
        order by j.updated_at desc
        limit 100
        for update
      loop
        select coalesce(array_agg(distinct t order by t), '{}')
          into v_candidate_tokens
        from unnest(regexp_split_to_array(
          regexp_replace(lower(coalesce(v_existing.task, '')), '[^[:alnum:]_ ]', ' ', 'g'),
          '[[:space:]]+'
        )) t
        where t <> '';

        if cardinality(v_candidate_tokens) < 6 then
          continue;
        end if;

        select coalesce(array_agg(t order by t), '{}')
          into v_candidate_numbers
        from unnest(v_candidate_tokens) t
        where t ~ '^[0-9]+([.,][0-9]+)?$';

        if v_task_numbers <> v_candidate_numbers then
          continue;
        end if;

        v_candidate_negated := v_candidate_tokens && array[
          'inte','ej','aldrig','inget','ingen','ingenting','utan',
          'not','never','no','without','stoppa','avbryt'
        ];
        if v_task_negated <> v_candidate_negated then
          continue;
        end if;

        select count(*) into v_overlap
        from unnest(v_task_tokens) t
        where t = any(v_candidate_tokens);

        if v_overlap::numeric / least(
          cardinality(v_task_tokens), cardinality(v_candidate_tokens)
        ) >= 0.90 then
          v_match := true;
          exit;
        end if;
      end loop;

      if not v_match then
        v_existing := null;
      end if;
    else
      v_existing := null;
    end if;
  end if;

  if v_existing.id is not null then
    v_tokens := coalesce(v_existing.access_token_hashes, '{}');
    if v_existing.access_token_hash is not null
       and not (v_existing.access_token_hash = any(v_tokens)) then
      v_tokens := array_append(v_tokens, v_existing.access_token_hash);
    end if;
    if not (p_token_hash = any(v_tokens)) then
      v_tokens := array_append(v_tokens, p_token_hash);
    end if;

    if v_existing.status in ('completed', 'failed') then
      update public.jarvis_jobs
      set access_token_hashes = v_tokens,
          dedupe_key = p_dedupe_key,
          status = 'queued',
          phase = 'Återupptaget efter en ny begäran – väntar på bakgrundsarbetare',
          history = coalesce(p_history, '[]'::jsonb),
          result = null,
          error = null,
          attempts = 0,
          started_at = null,
          locked_at = null,
          worker_id = null,
          notification_sent_at = null,
          completed_at = null,
          push_subscription = coalesce(p_push_subscription, push_subscription),
          updated_at = now()
      where id = v_existing.id
      returning status into v_status;
    else
      update public.jarvis_jobs
      set access_token_hashes = v_tokens,
          dedupe_key = coalesce(dedupe_key, p_dedupe_key),
          updated_at = now()
      where id = v_existing.id
      returning status into v_status;
    end if;

    return jsonb_build_object(
      'id', v_existing.id,
      'status', v_status,
      'deduplicated', true
    );
  end if;

  insert into public.jarvis_jobs (
    task, history, status, phase, access_token_hash,
    access_token_hashes, dedupe_key, push_subscription
  ) values (
    p_task, coalesce(p_history, '[]'::jsonb), 'queued',
    'Sparat – väntar på bakgrundsarbetare', p_token_hash,
    array[p_token_hash], p_dedupe_key, p_push_subscription
  )
  returning id, status into v_existing.id, v_status;

  return jsonb_build_object(
    'id', v_existing.id,
    'status', v_status,
    'deduplicated', false
  );
end;
$$;

revoke all on function public.jarvis_enqueue_job(text, text, text, jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.jarvis_enqueue_job(text, text, text, jsonb, jsonb) to service_role;
