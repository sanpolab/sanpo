-- にくきゅうレーダー 追加設定（第6弾）：散歩のルートと距離、体重、トイレ

alter table public.walks add column if not exists pet_id uuid references public.pets(id) on delete set null;
alter table public.walks add column if not exists distance_m int check (distance_m >= 0);
alter table public.walks add column if not exists route jsonb;
create index if not exists walks_pet_idx on public.walks (pet_id, started_at desc);

create table if not exists public.weights (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  pet_id uuid not null references public.pets(id) on delete cascade,
  measured_on date not null default current_date,
  kg numeric(5,2) not null check (kg > 0 and kg < 150),
  unique (pet_id, measured_on)
);
alter table public.weights enable row level security;
drop policy if exists "weights own" on public.weights;
create policy "weights own" on public.weights for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create table if not exists public.toilets (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  pet_id uuid references public.pets(id) on delete cascade,
  walk_id bigint references public.walks(id) on delete set null,
  kind text not null check (kind in ('pee','poo')),
  state text check (state in ('normal','soft','hard')),
  at timestamptz not null default now()
);
create index if not exists toilets_pet_idx on public.toilets (pet_id, at desc);
alter table public.toilets enable row level security;
drop policy if exists "toilets own" on public.toilets;
create policy "toilets own" on public.toilets for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
