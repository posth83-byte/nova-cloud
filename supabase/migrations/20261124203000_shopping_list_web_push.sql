create table if not exists public.shopping_list_push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  list_id uuid not null references public.shopping_lists(id) on delete cascade,
  endpoint text not null unique,
  subscription jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists shopping_list_push_subscriptions_list_idx
  on public.shopping_list_push_subscriptions (list_id);

alter table public.shopping_list_push_subscriptions enable row level security;
revoke all on table public.shopping_list_push_subscriptions from anon, authenticated;
grant all on table public.shopping_list_push_subscriptions to service_role;
