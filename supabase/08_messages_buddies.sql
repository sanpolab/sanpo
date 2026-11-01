-- にくきゅうレーダー 追加設定（第8弾）：メッセージ、散歩仲間、ユーザーの通報

-- ===== メッセージ =====
create table if not exists public.chats (
  id bigint generated always as identity primary key,
  user_a uuid not null references public.profiles(id) on delete cascade,
  user_b uuid not null references public.profiles(id) on delete cascade,
  requested_by uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  status text not null default 'pending' check (status in ('pending','accepted')),
  created_at timestamptz not null default now(),
  last_at timestamptz not null default now(),
  unique (user_a, user_b),
  check (user_a < user_b)
);
create index if not exists chats_a_idx on public.chats (user_a, last_at desc);
create index if not exists chats_b_idx on public.chats (user_b, last_at desc);

-- 相手がこちらをフォローしていれば、最初から承認済み
create or replace function public.chat_set_status() returns trigger
language plpgsql security definer set search_path = public as
$$ declare other uuid; begin
  other := case when new.user_a = new.requested_by then new.user_b else new.user_a end;
  new.status := case when exists (select 1 from public.follows where follower_id = other and followee_id = new.requested_by and status = 'accepted') then 'accepted' else 'pending' end;
  return new;
end $$;
drop trigger if exists chats_status on public.chats;
create trigger chats_status before insert on public.chats for each row execute function public.chat_set_status();

alter table public.chats enable row level security;
drop policy if exists "chats read member" on public.chats;
create policy "chats read member" on public.chats for select using (auth.uid() in (user_a, user_b));
drop policy if exists "chats insert member" on public.chats;
create policy "chats insert member" on public.chats for insert with check (
  requested_by = auth.uid() and auth.uid() in (user_a, user_b)
  and not public.is_blocked(case when user_a = auth.uid() then user_b else user_a end));
drop policy if exists "chats accept" on public.chats;
create policy "chats accept" on public.chats for update
  using (auth.uid() in (user_a, user_b) and auth.uid() <> requested_by)
  with check (auth.uid() in (user_a, user_b) and status = 'accepted');
drop policy if exists "chats delete member" on public.chats;
create policy "chats delete member" on public.chats for delete using (auth.uid() in (user_a, user_b));

create table if not exists public.messages (
  id bigint generated always as identity primary key,
  chat_id bigint not null references public.chats(id) on delete cascade,
  sender_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  body text not null check (char_length(body) between 1 and 500),
  created_at timestamptz not null default now(),
  read_at timestamptz
);
create index if not exists messages_chat_idx on public.messages (chat_id, created_at);

create or replace function public.chat_member(cid bigint) returns boolean
language sql stable security definer set search_path = public as
$$ select exists (select 1 from public.chats where id = cid and auth.uid() in (user_a, user_b)) $$;
-- 送ってよいか：承認済み、またはリクエストした本人が最初の1通だけ
create or replace function public.can_send(cid bigint) returns boolean
language sql stable security definer set search_path = public as
$$ select exists (
  select 1 from public.chats c where c.id = cid and auth.uid() in (c.user_a, c.user_b)
    and not public.is_blocked(case when c.user_a = auth.uid() then c.user_b else c.user_a end)
    and (c.status = 'accepted' or (c.requested_by = auth.uid() and not exists (select 1 from public.messages m where m.chat_id = cid)))
) $$;

alter table public.messages enable row level security;
drop policy if exists "messages read member" on public.messages;
create policy "messages read member" on public.messages for select using (public.chat_member(chat_id));
drop policy if exists "messages send" on public.messages;
create policy "messages send" on public.messages for insert with check (sender_id = auth.uid() and public.can_send(chat_id));
drop policy if exists "messages mark read" on public.messages;
create policy "messages mark read" on public.messages for update using (public.chat_member(chat_id) and sender_id <> auth.uid()) with check (public.chat_member(chat_id) and sender_id <> auth.uid());

-- お知らせ：メッセージ
alter table public.notifications drop constraint if exists notifications_kind_check;
alter table public.notifications add constraint notifications_kind_check check (kind in ('like','comment','follow','follow_request','follow_accept','message'));
create or replace function public.on_message() returns trigger
language plpgsql security definer set search_path = public as
$$ declare c record; other uuid; begin
  select * into c from public.chats where id = new.chat_id;
  update public.chats set last_at = new.created_at where id = new.chat_id;
  other := case when c.user_a = new.sender_id then c.user_b else c.user_a end;
  delete from public.notifications where user_id = other and actor_id = new.sender_id and kind = 'message' and not read;
  insert into public.notifications (user_id, actor_id, kind) values (other, new.sender_id, 'message');
  return new;
end $$;
drop trigger if exists messages_after on public.messages;
create trigger messages_after after insert on public.messages for each row execute function public.on_message();

-- ===== 散歩仲間 =====
create table if not exists public.buddies (
  user_id uuid primary key default auth.uid() references public.profiles(id) on delete cascade,
  area_name text not null default '' check (char_length(area_name) <= 60),
  lat_grid numeric(6,2) not null,
  lon_grid numeric(6,2) not null,
  times text[] not null default '{}',
  note text not null default '' check (char_length(note) <= 120),
  updated_at timestamptz not null default now()
);
create index if not exists buddies_grid_idx on public.buddies (lat_grid, lon_grid);
alter table public.buddies enable row level security;
drop policy if exists "buddies read" on public.buddies;
create policy "buddies read" on public.buddies for select using (auth.uid() is not null and not public.is_blocked(user_id));
drop policy if exists "buddies own" on public.buddies;
create policy "buddies own" on public.buddies for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ===== ユーザーの通報 =====
create table if not exists public.user_reports (
  id bigint generated always as identity primary key,
  reporter_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  target_id uuid not null references public.profiles(id) on delete cascade,
  reason text not null default '' check (char_length(reason) <= 100),
  created_at timestamptz not null default now(),
  unique (reporter_id, target_id)
);
alter table public.user_reports enable row level security;
drop policy if exists "user_reports insert own" on public.user_reports;
create policy "user_reports insert own" on public.user_reports for insert with check (auth.uid() = reporter_id);
drop policy if exists "user_reports admin read" on public.user_reports;
create policy "user_reports admin read" on public.user_reports for select using (public.is_admin());
drop policy if exists "user_reports admin delete" on public.user_reports;
create policy "user_reports admin delete" on public.user_reports for delete using (public.is_admin());
