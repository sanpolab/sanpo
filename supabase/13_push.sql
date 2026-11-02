-- にくきゅうレーダー 追加設定（第13弾）：プッシュ通知

-- iPhoneごとの通知先（本人だけが登録・削除できる。中身は本人にしか見えない）
create table if not exists public.push_tokens (
  token text primary key check (char_length(token) between 32 and 200),
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  platform text not null default 'ios' check (platform in ('ios')),
  updated_at timestamptz not null default now()
);
create index if not exists push_tokens_user_idx on public.push_tokens (user_id);
alter table public.push_tokens enable row level security;
drop policy if exists "push_tokens own" on public.push_tokens;
create policy "push_tokens own" on public.push_tokens for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- 同じ通知を2回送らないための印
alter table public.notifications add column if not exists pushed_at timestamptz;

-- お知らせが増えたら、送信のプログラムに「この番号のお知らせを送って」と頼む
-- （プログラムは番号しか受け取らず、文面はデータベースから自分で作るので、外から変な通知を送らせることはできない）
create extension if not exists pg_net with schema extensions;
create or replace function public.push_notify() returns trigger
language plpgsql security definer set search_path = public, extensions as
$$ begin
  perform net.http_post(
    url := 'https://odwucmmcxbdyhncxdwvg.supabase.co/functions/v1/push',
    body := jsonb_build_object('id', new.id),
    headers := '{"Content-Type":"application/json"}'::jsonb);
  return new;
exception when others then
  return new; -- 通知が送れなくても、いいね等の操作は止めない
end $$;
drop trigger if exists notifications_push on public.notifications;
create trigger notifications_push after insert on public.notifications for each row execute function public.push_notify();
