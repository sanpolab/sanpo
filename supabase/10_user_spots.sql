-- にくきゅうレーダー 追加設定（第10弾）：みんなが追加するドッグラン・カフェ

create table if not exists public.user_spots (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 60),
  spot_type text not null check (spot_type in ('dogpark','cafe')),
  lat numeric(8,5) not null,
  lon numeric(8,5) not null,
  note text not null default '' check (char_length(note) <= 200),
  created_at timestamptz not null default now()
);
create index if not exists user_spots_geo_idx on public.user_spots (lat, lon);

create table if not exists public.spot_reports (
  id bigint generated always as identity primary key,
  spot_id bigint not null references public.user_spots(id) on delete cascade,
  reporter_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  reason text not null default '' check (char_length(reason) <= 100),
  created_at timestamptz not null default now(),
  unique (spot_id, reporter_id)
);

create or replace function public.spot_report_count(sid bigint) returns int
language sql stable security definer set search_path = public as
$$ select count(*)::int from public.spot_reports where spot_id = sid $$;

alter table public.user_spots enable row level security;
drop policy if exists "user_spots read" on public.user_spots;
create policy "user_spots read" on public.user_spots for select using (
  auth.uid() = user_id or public.is_admin()
  or (public.spot_report_count(id) < 3 and not public.is_blocked(user_id)));
drop policy if exists "user_spots own" on public.user_spots;
create policy "user_spots own" on public.user_spots for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "user_spots admin delete" on public.user_spots;
create policy "user_spots admin delete" on public.user_spots for delete using (public.is_admin());

alter table public.spot_reports enable row level security;
drop policy if exists "spot_reports insert own" on public.spot_reports;
create policy "spot_reports insert own" on public.spot_reports for insert with check (auth.uid() = reporter_id);
drop policy if exists "spot_reports admin read" on public.spot_reports;
create policy "spot_reports admin read" on public.spot_reports for select using (public.is_admin());
drop policy if exists "spot_reports admin delete" on public.spot_reports;
create policy "spot_reports admin delete" on public.spot_reports for delete using (public.is_admin());

-- 場所を消したら、その場所への口コミも消す
create or replace function public.user_spot_cleanup() returns trigger
language plpgsql security definer set search_path = public as
$$ begin delete from public.spot_reviews where osm_id = 'u/' || old.id; return old; end $$;
drop trigger if exists user_spots_cleanup on public.user_spots;
create trigger user_spots_cleanup after delete on public.user_spots for each row execute function public.user_spot_cleanup();
