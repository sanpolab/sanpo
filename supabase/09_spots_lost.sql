-- にくきゅうレーダー 追加設定（第9弾）：ドッグラン・カフェの口コミ、迷子掲示板

-- ===== 口コミ =====
create table if not exists public.spot_reviews (
  id bigint generated always as identity primary key,
  osm_id text not null check (char_length(osm_id) <= 40),
  spot_name text not null default '' check (char_length(spot_name) <= 80),
  spot_type text not null default '' check (spot_type in ('dogpark','cafe','')),
  lat numeric(8,5), lon numeric(8,5),
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  stars smallint not null check (stars between 1 and 5),
  body text not null default '' check (char_length(body) <= 200),
  created_at timestamptz not null default now(),
  unique (osm_id, user_id)
);
create index if not exists spot_reviews_osm_idx on public.spot_reviews (osm_id, created_at desc);
alter table public.spot_reviews enable row level security;
drop policy if exists "spot_reviews read" on public.spot_reviews;
create policy "spot_reviews read" on public.spot_reviews for select using (not public.is_blocked(user_id));
drop policy if exists "spot_reviews own" on public.spot_reviews;
create policy "spot_reviews own" on public.spot_reviews for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "spot_reviews admin delete" on public.spot_reviews;
create policy "spot_reviews admin delete" on public.spot_reviews for delete using (public.is_admin());

-- ===== 迷子掲示板 =====
create table if not exists public.lost_pets (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  kind text not null check (kind in ('lost','found')),
  species text not null default 'dog' check (species in ('dog','cat','other')),
  name text not null default '' check (char_length(name) <= 30),
  description text not null default '' check (char_length(description) <= 400),
  image_path text,
  lat numeric(7,3) not null,      -- 約100m単位
  lon numeric(7,3) not null,
  area_name text not null default '' check (char_length(area_name) <= 60),
  seen_at timestamptz not null default now(),
  status text not null default 'open' check (status in ('open','resolved')),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default now() + interval '30 days'
);
create index if not exists lost_pets_geo_idx on public.lost_pets (lat, lon);
alter table public.lost_pets enable row level security;
drop policy if exists "lost_pets read" on public.lost_pets;
create policy "lost_pets read" on public.lost_pets for select using (
  auth.uid() = user_id or public.is_admin() or (expires_at > now() and not public.is_blocked(user_id)));
drop policy if exists "lost_pets own" on public.lost_pets;
create policy "lost_pets own" on public.lost_pets for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "lost_pets admin delete" on public.lost_pets;
create policy "lost_pets admin delete" on public.lost_pets for delete using (public.is_admin());
