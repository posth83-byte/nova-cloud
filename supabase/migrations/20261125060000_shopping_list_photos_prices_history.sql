alter table public.shopping_list_items
  add column if not exists price numeric(10,2),
  add column if not exists image_data text,
  add column if not exists is_favorite boolean not null default false;

create table if not exists public.shopping_list_history (
  id uuid primary key default gen_random_uuid(),
  list_id uuid not null references public.shopping_lists(id) on delete cascade,
  original_item_id uuid,
  name text not null,
  category text not null default 'Övrigt',
  qty text not null default '',
  price numeric(10,2),
  image_data text,
  purchased_at timestamptz not null default now()
);

create index if not exists shopping_list_history_list_purchased_idx
  on public.shopping_list_history(list_id, purchased_at desc);

alter table public.shopping_list_history enable row level security;
