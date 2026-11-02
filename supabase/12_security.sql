-- にくきゅうレーダー 追加設定（第12弾）：公開前の安全チェックで見つかった問題の修正

-- ===== 写真の場所は「自分のフォルダ/ファイル名」の形だけ（悪意のある文字を入れさせない） =====
alter table public.profiles drop constraint if exists profiles_avatar_path_check;
alter table public.profiles add constraint profiles_avatar_path_check
  check (avatar_path is null or (avatar_path ~ '^[0-9a-f-]{36}/[A-Za-z0-9._-]{1,80}$' and split_part(avatar_path,'/',1) = id::text)) not valid;
alter table public.posts drop constraint if exists posts_image_path_check;
alter table public.posts add constraint posts_image_path_check
  check (image_path ~ '^[0-9a-f-]{36}/[A-Za-z0-9._-]{1,80}$' and split_part(image_path,'/',1) = user_id::text) not valid;
alter table public.lost_pets drop constraint if exists lost_pets_image_path_check;
alter table public.lost_pets add constraint lost_pets_image_path_check
  check (image_path is null or (image_path ~ '^[0-9a-f-]{36}/[A-Za-z0-9._-]{1,80}$' and split_part(image_path,'/',1) = user_id::text)) not valid;

-- ===== メッセージ：受け取った側が変えられるのは「既読」だけ =====
create or replace function public.messages_guard() returns trigger
language plpgsql set search_path = public as
$$ begin
  if new.body is distinct from old.body or new.chat_id is distinct from old.chat_id
     or new.sender_id is distinct from old.sender_id or new.created_at is distinct from old.created_at then
    raise exception 'only read_at can be changed';
  end if;
  return new;
end $$;
drop trigger if exists messages_guard on public.messages;
create trigger messages_guard before update on public.messages for each row execute function public.messages_guard();

-- 承認前の「最初の1通だけ」を、同時に送っても守る
create or replace function public.messages_first_only() returns trigger
language plpgsql security definer set search_path = public as
$$ declare c record; begin
  select * into c from public.chats where id = new.chat_id for update;
  if c.status = 'pending' and exists (select 1 from public.messages where chat_id = new.chat_id) then
    raise exception 'wait until the request is accepted';
  end if;
  return new;
end $$;
drop trigger if exists messages_first_only on public.messages;
create trigger messages_first_only before insert on public.messages for each row execute function public.messages_first_only();

-- ===== メッセージの部屋：承認で変えられるのは状態だけ =====
create or replace function public.chats_guard() returns trigger
language plpgsql set search_path = public as
$$ begin
  if new.user_a is distinct from old.user_a or new.user_b is distinct from old.user_b
     or new.requested_by is distinct from old.requested_by or new.created_at is distinct from old.created_at then
    raise exception 'chat members cannot be changed';
  end if;
  return new;
end $$;
drop trigger if exists chats_guard on public.chats;
create trigger chats_guard before update on public.chats for each row execute function public.chats_guard();

-- 承認前のリクエストは、送った側は消せない（消して作り直して何度も送るのを防ぐ）
drop policy if exists "chats delete member" on public.chats;
create policy "chats delete member" on public.chats for delete using (
  auth.uid() in (user_a, user_b) and (status = 'accepted' or auth.uid() <> requested_by));

-- ===== フォロー：承認で変えられるのは状態だけ =====
create or replace function public.follows_guard() returns trigger
language plpgsql set search_path = public as
$$ begin
  if new.follower_id is distinct from old.follower_id or new.followee_id is distinct from old.followee_id then
    raise exception 'follow members cannot be changed';
  end if;
  return new;
end $$;
drop trigger if exists follows_guard on public.follows;
create trigger follows_guard before update on public.follows for each row execute function public.follows_guard();

-- ===== ブロックされた相手・見られない投稿には、いいね・コメント・フォローできない =====
drop policy if exists "likes insert own" on public.likes;
create policy "likes insert own" on public.likes for insert with check (
  auth.uid() = user_id and exists (select 1 from public.posts p where p.id = post_id));
drop policy if exists "comments insert own" on public.comments;
create policy "comments insert own" on public.comments for insert with check (
  auth.uid() = user_id and exists (select 1 from public.posts p where p.id = post_id));
drop policy if exists "follows insert own" on public.follows;
create policy "follows insert own" on public.follows for insert with check (
  auth.uid() = follower_id and followee_id <> auth.uid() and not public.is_blocked(followee_id));

-- いいねは、見られる投稿のものだけ見える
drop policy if exists "likes read" on public.likes;
create policy "likes read" on public.likes for select using (exists (select 1 from public.posts p where p.id = post_id));

-- 承認待ちのフォローリクエストは、本人たち以外には見えない
drop policy if exists "follows read" on public.follows;
create policy "follows read" on public.follows for select using (
  auth.uid() = follower_id or auth.uid() = followee_id
  or (status = 'accepted'
      and not exists (select 1 from public.profiles p where p.id in (follower_id, followee_id) and p.hide_follows)));

-- ===== 通報で自動的に隠すのは、登録から3日以上たった人の通報が3件以上のとき =====
-- （作ったばかりのアカウントを集めて、気に入らない投稿を隠すのを防ぐ）
create or replace function public.report_count(p bigint) returns int
language sql stable security definer set search_path = public as
$$ select count(*)::int from public.reports r join public.profiles pr on pr.id = r.reporter_id
   where r.post_id = p and pr.created_at < r.created_at - interval '3 days' $$;
create or replace function public.spot_report_count(sid bigint) returns int
language sql stable security definer set search_path = public as
$$ select count(*)::int from public.spot_reports r join public.profiles pr on pr.id = r.reporter_id
   where r.spot_id = sid and pr.created_at < r.created_at - interval '3 days' $$;
