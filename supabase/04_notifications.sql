-- にくきゅうレーダー 追加設定（第4弾）：お知らせ（いいね・コメント・フォロー）

create table if not exists public.notifications (
  id bigint generated always as identity primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,   -- 受け取る人
  actor_id uuid not null references public.profiles(id) on delete cascade,  -- した人
  kind text not null check (kind in ('like','comment','follow','follow_request','follow_accept')),
  post_id bigint references public.posts(id) on delete cascade,
  comment_id bigint references public.comments(id) on delete cascade,
  read boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists notifications_user_idx on public.notifications (user_id, created_at desc);

alter table public.notifications enable row level security;
drop policy if exists "notifications read own" on public.notifications;
create policy "notifications read own" on public.notifications for select using (auth.uid() = user_id);
drop policy if exists "notifications update own" on public.notifications;
create policy "notifications update own" on public.notifications for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "notifications delete own" on public.notifications;
create policy "notifications delete own" on public.notifications for delete using (auth.uid() = user_id);

-- いいね
create or replace function public.notify_like() returns trigger
language plpgsql security definer set search_path = public as
$$ declare owner uuid; begin
  if tg_op = 'INSERT' then
    select user_id into owner from public.posts where id = new.post_id;
    if owner is not null and owner <> new.user_id then
      insert into public.notifications (user_id, actor_id, kind, post_id) values (owner, new.user_id, 'like', new.post_id);
    end if;
    return new;
  else
    delete from public.notifications where kind = 'like' and actor_id = old.user_id and post_id = old.post_id;
    return old;
  end if;
end $$;
drop trigger if exists likes_notify on public.likes;
create trigger likes_notify after insert or delete on public.likes for each row execute function public.notify_like();

-- コメント
create or replace function public.notify_comment() returns trigger
language plpgsql security definer set search_path = public as
$$ declare owner uuid; begin
  select user_id into owner from public.posts where id = new.post_id;
  if owner is not null and owner <> new.user_id then
    insert into public.notifications (user_id, actor_id, kind, post_id, comment_id) values (owner, new.user_id, 'comment', new.post_id, new.id);
  end if;
  return new;
end $$;
drop trigger if exists comments_notify on public.comments;
create trigger comments_notify after insert on public.comments for each row execute function public.notify_comment();

-- フォロー・リクエスト・承認
create or replace function public.notify_follow() returns trigger
language plpgsql security definer set search_path = public as
$$ begin
  if tg_op = 'INSERT' then
    insert into public.notifications (user_id, actor_id, kind)
    values (new.followee_id, new.follower_id, case when new.status = 'pending' then 'follow_request' else 'follow' end);
    return new;
  elsif tg_op = 'UPDATE' then
    if old.status = 'pending' and new.status = 'accepted' then
      delete from public.notifications where kind = 'follow_request' and user_id = new.followee_id and actor_id = new.follower_id;
      insert into public.notifications (user_id, actor_id, kind) values (new.follower_id, new.followee_id, 'follow_accept');
    end if;
    return new;
  else
    delete from public.notifications where kind in ('follow','follow_request') and user_id = old.followee_id and actor_id = old.follower_id;
    return old;
  end if;
end $$;
drop trigger if exists follows_notify on public.follows;
create trigger follows_notify after insert or update or delete on public.follows for each row execute function public.notify_follow();
