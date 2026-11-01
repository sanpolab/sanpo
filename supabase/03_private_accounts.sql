-- にくきゅうレーダー 追加設定（第3弾）：鍵アカウント

alter table public.profiles add column if not exists is_private boolean not null default false;

-- フォローに「リクエスト中」「承認済み」の状態を持たせる
alter table public.follows add column if not exists status text not null default 'accepted';
alter table public.follows drop constraint if exists follows_status_check;
alter table public.follows add constraint follows_status_check check (status in ('pending','accepted'));

-- フォローするとき：相手が鍵アカウントならリクエスト中、そうでなければすぐフォロー
create or replace function public.follow_set_status() returns trigger
language plpgsql security definer set search_path = public as
$$ begin
  if tg_op = 'INSERT' then
    new.status := case when (select is_private from public.profiles where id = new.followee_id) then 'pending' else 'accepted' end;
  end if;
  return new;
end $$;
drop trigger if exists follows_status on public.follows;
create trigger follows_status before insert on public.follows
for each row execute function public.follow_set_status();

-- 鍵を外したら、届いていたリクエストはまとめて承認
create or replace function public.unlock_accept_pending() returns trigger
language plpgsql security definer set search_path = public as
$$ begin
  if old.is_private and not new.is_private then
    update public.follows set status = 'accepted' where followee_id = new.id and status = 'pending';
  end if;
  return new;
end $$;
drop trigger if exists profiles_unlock on public.profiles;
create trigger profiles_unlock after update of is_private on public.profiles
for each row execute function public.unlock_accept_pending();

-- 投稿を見てよいか：本人、鍵なし、または承認済みフォロワー
create or replace function public.can_view(owner uuid) returns boolean
language sql stable security definer set search_path = public as
$$ select owner = auth.uid()
     or not coalesce((select is_private from public.profiles where id = owner), false)
     or exists (select 1 from public.follows where follower_id = auth.uid() and followee_id = owner and status = 'accepted') $$;

drop policy if exists "posts read" on public.posts;
create policy "posts read" on public.posts for select
using ((public.report_count(id) < 3 or auth.uid() = user_id) and not public.is_blocked(user_id) and public.can_view(user_id));

drop policy if exists "comments read" on public.comments;
create policy "comments read" on public.comments for select
using (not public.is_blocked(user_id) and exists (select 1 from public.posts p where p.id = post_id));

-- 承認：フォローされた側が status を accepted にできる
drop policy if exists "follows approve" on public.follows;
create policy "follows approve" on public.follows for update
using (auth.uid() = followee_id) with check (auth.uid() = followee_id and status = 'accepted');

-- 拒否・フォロワーを外す：フォローされた側も消せる
drop policy if exists "follows delete own" on public.follows;
create policy "follows delete own" on public.follows for delete
using (auth.uid() = follower_id or auth.uid() = followee_id);
