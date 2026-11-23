create table if not exists public.shopping_lists (
  id uuid primary key default gen_random_uuid(),
  token_hash text not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.shopping_list_items (
  id uuid primary key default gen_random_uuid(),
  list_id uuid not null references public.shopping_lists(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 120),
  category text not null default 'Övrigt',
  qty text not null default '',
  done boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists shopping_list_items_list_created_idx
  on public.shopping_list_items (list_id, created_at desc);
create index if not exists shopping_list_items_list_updated_idx
  on public.shopping_list_items (list_id, updated_at desc);

alter table public.shopping_lists enable row level security;
alter table public.shopping_list_items enable row level security;

revoke all on table public.shopping_lists from anon, authenticated;
revoke all on table public.shopping_list_items from anon, authenticated;
grant all on table public.shopping_lists to service_role;
grant all on table public.shopping_list_items to service_role;

create or replace function public.touch_shopping_list_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
declare
  affected_list_id uuid;
begin
  if tg_op = 'DELETE' then
    affected_list_id := old.list_id;
  else
    affected_list_id := new.list_id;
    new.updated_at := now();
  end if;

  update public.shopping_lists
  set updated_at = now()
  where id = affected_list_id;

  if tg_op = 'DELETE' then
    return old;
  end if;
  return new;
end;
$$;

drop trigger if exists shopping_list_items_touch_parent on public.shopping_list_items;
create trigger shopping_list_items_touch_parent
before insert or update or delete on public.shopping_list_items
for each row execute function public.touch_shopping_list_updated_at();
