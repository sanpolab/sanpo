-- にくきゅうレーダー 追加設定（第7弾）：ID検索、フォロー一覧を隠す、公式アカウント、通報の管理

-- ID（@から始まる名前）と公開の設定
alter table public.profiles add column if not exists handle text;
alter table public.profiles drop constraint if exists profiles_handle_check;
alter table public.profiles add constraint profiles_handle_check check (handle ~ '^[a-z0-9_]{3,20}$');
create unique index if not exists profiles_handle_key on public.profiles (handle);
alter table public.profiles add column if not exists searchable boolean not null default true;
alter table public.profiles add column if not exists hide_follows boolean not null default false;
alter table public.profiles add column if not exists is_official boolean not null default false;

-- 管理者
create table if not exists public.admins (user_id uuid primary key references public.profiles(id) on delete cascade);
alter table public.admins enable row level security;
drop policy if exists "admins read self" on public.admins;
create policy "admins read self" on public.admins for select using (auth.uid() = user_id);
create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as
$$ select exists (select 1 from public.admins where user_id = auth.uid()) $$;

-- 公式マークは管理者しか付け外しできない
create or replace function public.guard_official() returns trigger
language plpgsql security definer set search_path = public as
$$ begin
  if new.is_official is distinct from old.is_official and auth.uid() is not null and not public.is_admin() then
    new.is_official := old.is_official;
  end if;
  return new;
end $$;
drop trigger if exists profiles_guard_official on public.profiles;
create trigger profiles_guard_official before update on public.profiles for each row execute function public.guard_official();
drop policy if exists "profiles admin update" on public.profiles;
create policy "profiles admin update" on public.profiles for update using (public.is_admin()) with check (public.is_admin());

-- フォロー一覧：隠している人の一覧は、本人以外には見えない（人数だけ出す）
drop policy if exists "follows read" on public.follows;
create policy "follows read" on public.follows for select using (
  auth.uid() = follower_id or auth.uid() = followee_id
  or not exists (select 1 from public.profiles p where p.id in (follower_id, followee_id) and p.hide_follows)
);
create or replace function public.follow_counts(uid uuid) returns table (followers int, following int)
language sql stable security definer set search_path = public as
$$ select (select count(*)::int from public.follows where followee_id = uid and status = 'accepted'),
          (select count(*)::int from public.follows where follower_id = uid and status = 'accepted') $$;

-- 管理者：通報を見る・消す、問題のある投稿を消す、非表示になった投稿も見る
drop policy if exists "reports admin read" on public.reports;
create policy "reports admin read" on public.reports for select using (public.is_admin());
drop policy if exists "reports admin delete" on public.reports;
create policy "reports admin delete" on public.reports for delete using (public.is_admin());

drop policy if exists "posts read" on public.posts;
create policy "posts read" on public.posts for select
using (public.is_admin() or ((public.report_count(id) < 3 or auth.uid() = user_id) and not public.is_blocked(user_id) and public.can_view(user_id)));
drop policy if exists "posts admin delete" on public.posts;
create policy "posts admin delete" on public.posts for delete using (public.is_admin());
drop policy if exists "comments admin delete" on public.comments;
create policy "comments admin delete" on public.comments for delete using (public.is_admin());
drop policy if exists "photos admin delete" on storage.objects;
create policy "photos admin delete" on storage.objects for delete to authenticated using (bucket_id = 'photos' and public.is_admin());
