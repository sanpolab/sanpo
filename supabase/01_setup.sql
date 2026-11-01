-- さんぽ路面計 データベース設定
-- Supabase の「SQL Editor」に全部貼り付けて「Run」を1回押すだけで設定が完了します。

-- ===== プロフィール（飼い主と犬） =====
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  nickname text not null default '飼い主さん' check (char_length(nickname) <= 30),
  dog_name text not null default '' check (char_length(dog_name) <= 30),
  dog_breed text not null default '' check (char_length(dog_breed) <= 40),
  dog_size text not null default 'small' check (dog_size in ('small','medium','large')),
  dog_age text not null default 'adult' check (dog_age in ('puppy','adult','senior')),
  brachy boolean not null default false,
  avatar_path text,
  created_at timestamptz not null default now()
);

-- ===== 投稿 =====
create table if not exists public.posts (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  image_path text not null,
  caption text not null default '' check (char_length(caption) <= 300),
  area_name text not null default '' check (char_length(area_name) <= 60),
  lat_grid numeric(6,2),   -- 約1km四方に丸めた位置だけを保存（正確な位置は保存しない）
  lon_grid numeric(6,2),
  created_at timestamptz not null default now()
);
create index if not exists posts_created_idx on public.posts (created_at desc);
create index if not exists posts_grid_idx on public.posts (lat_grid, lon_grid);

create table if not exists public.likes (
  post_id bigint references public.posts(id) on delete cascade,
  user_id uuid default auth.uid() references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (post_id, user_id)
);

create table if not exists public.comments (
  id bigint generated always as identity primary key,
  post_id bigint not null references public.posts(id) on delete cascade,
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  body text not null check (char_length(body) between 1 and 200),
  created_at timestamptz not null default now()
);
create index if not exists comments_post_idx on public.comments (post_id, created_at);

create table if not exists public.follows (
  follower_id uuid default auth.uid() references public.profiles(id) on delete cascade,
  followee_id uuid references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (follower_id, followee_id),
  check (follower_id <> followee_id)
);

create table if not exists public.reports (
  id bigint generated always as identity primary key,
  post_id bigint not null references public.posts(id) on delete cascade,
  reporter_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  reason text not null default '' check (char_length(reason) <= 100),
  created_at timestamptz not null default now(),
  unique (post_id, reporter_id)
);

-- 通報が3件たまった投稿は自動で非表示
create or replace function public.report_count(p bigint) returns int
language sql stable security definer set search_path = public as
$$ select count(*)::int from public.reports where post_id = p $$;

-- 新規登録時にプロフィールを自動作成
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as
$$ begin insert into public.profiles (id) values (new.id) on conflict do nothing; return new; end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute function public.handle_new_user();

-- ===== アクセスルール =====
alter table public.profiles enable row level security;
alter table public.posts    enable row level security;
alter table public.likes    enable row level security;
alter table public.comments enable row level security;
alter table public.follows  enable row level security;
alter table public.reports  enable row level security;

drop policy if exists "profiles read" on public.profiles;
create policy "profiles read" on public.profiles for select using (true);
drop policy if exists "profiles update own" on public.profiles;
create policy "profiles update own" on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);

drop policy if exists "posts read" on public.posts;
create policy "posts read" on public.posts for select using (public.report_count(id) < 3 or auth.uid() = user_id);
drop policy if exists "posts insert own" on public.posts;
create policy "posts insert own" on public.posts for insert with check (auth.uid() = user_id);
drop policy if exists "posts delete own" on public.posts;
create policy "posts delete own" on public.posts for delete using (auth.uid() = user_id);

drop policy if exists "likes read" on public.likes;
create policy "likes read" on public.likes for select using (true);
drop policy if exists "likes insert own" on public.likes;
create policy "likes insert own" on public.likes for insert with check (auth.uid() = user_id);
drop policy if exists "likes delete own" on public.likes;
create policy "likes delete own" on public.likes for delete using (auth.uid() = user_id);

drop policy if exists "comments read" on public.comments;
create policy "comments read" on public.comments for select using (true);
drop policy if exists "comments insert own" on public.comments;
create policy "comments insert own" on public.comments for insert with check (auth.uid() = user_id);
drop policy if exists "comments delete own" on public.comments;
create policy "comments delete own" on public.comments for delete using (auth.uid() = user_id);

drop policy if exists "follows read" on public.follows;
create policy "follows read" on public.follows for select using (true);
drop policy if exists "follows insert own" on public.follows;
create policy "follows insert own" on public.follows for insert with check (auth.uid() = follower_id);
drop policy if exists "follows delete own" on public.follows;
create policy "follows delete own" on public.follows for delete using (auth.uid() = follower_id);

-- 通報は送るだけ（誰が通報したかは他の人から見えない）
drop policy if exists "reports insert own" on public.reports;
create policy "reports insert own" on public.reports for insert with check (auth.uid() = reporter_id);

-- ===== 写真の保存場所 =====
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('photos', 'photos', true, 3145728, array['image/jpeg','image/webp'])
on conflict (id) do update set public = true, file_size_limit = 3145728, allowed_mime_types = array['image/jpeg','image/webp'];

drop policy if exists "photos upload own folder" on storage.objects;
create policy "photos upload own folder" on storage.objects for insert to authenticated
with check (bucket_id = 'photos' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists "photos delete own" on storage.objects;
create policy "photos delete own" on storage.objects for delete to authenticated
using (bucket_id = 'photos' and (storage.foldername(name))[1] = auth.uid()::text);
