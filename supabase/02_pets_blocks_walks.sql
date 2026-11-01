-- さんぽ路面計 追加設定（第2弾）：猫対応・ブロック・散歩の記録・アカウント削除

-- 猫にも対応
alter table public.profiles add column if not exists pet_type text not null default 'dog';
alter table public.profiles drop constraint if exists profiles_pet_type_check;
alter table public.profiles add constraint profiles_pet_type_check check (pet_type in ('dog','cat'));

-- ブロック
create table if not exists public.blocks (
  blocker_id uuid default auth.uid() references public.profiles(id) on delete cascade,
  blocked_id uuid references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (blocker_id, blocked_id),
  check (blocker_id <> blocked_id)
);
alter table public.blocks enable row level security;
drop policy if exists "blocks read own" on public.blocks;
create policy "blocks read own" on public.blocks for select using (auth.uid() = blocker_id);
drop policy if exists "blocks insert own" on public.blocks;
create policy "blocks insert own" on public.blocks for insert with check (auth.uid() = blocker_id);
drop policy if exists "blocks delete own" on public.blocks;
create policy "blocks delete own" on public.blocks for delete using (auth.uid() = blocker_id);

-- どちらかがブロックしていたら、お互いの投稿とコメントが見えなくなる
create or replace function public.is_blocked(target uuid) returns boolean
language sql stable security definer set search_path = public as
$$ select exists (select 1 from public.blocks
     where (blocker_id = auth.uid() and blocked_id = target)
        or (blocker_id = target and blocked_id = auth.uid())) $$;

drop policy if exists "posts read" on public.posts;
create policy "posts read" on public.posts for select
using ((public.report_count(id) < 3 or auth.uid() = user_id) and not public.is_blocked(user_id));
drop policy if exists "comments read" on public.comments;
create policy "comments read" on public.comments for select using (not public.is_blocked(user_id));

-- 散歩の記録（本人だけが見られる）
create table if not exists public.walks (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  started_at timestamptz not null,
  minutes int not null check (minutes between 1 and 600),
  level smallint check (level between 0 and 3),
  asph smallint,
  created_at timestamptz not null default now()
);
create index if not exists walks_user_idx on public.walks (user_id, started_at desc);
alter table public.walks enable row level security;
drop policy if exists "walks own" on public.walks;
create policy "walks own" on public.walks for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- アカウント削除（本人のデータがすべて消える）
create or replace function public.delete_account() returns void
language plpgsql security definer set search_path = public, auth as
$$ begin
  if auth.uid() is null then raise exception 'not signed in'; end if;
  delete from auth.users where id = auth.uid();
end $$;
revoke all on function public.delete_account() from public, anon;
grant execute on function public.delete_account() to authenticated;
