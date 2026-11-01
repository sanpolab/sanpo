-- にくきゅうレーダー 追加設定（第5弾）：複数のうちの子

create table if not exists public.pets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  name text not null default '' check (char_length(name) <= 20),
  species text not null default 'dog' check (species in ('dog','cat')),
  size text not null default 'small' check (size in ('small','medium','large')),
  age text not null default 'adult' check (age in ('puppy','adult','senior')),
  brachy boolean not null default false,
  coat text not null default 'mid' check (coat in ('light','mid','dark')),
  hair text not null default 'short' check (hair in ('short','long','double')),
  conds text[] not null default '{}',
  created_at timestamptz not null default now()
);
create index if not exists pets_user_idx on public.pets (user_id, created_at);
alter table public.pets enable row level security;
drop policy if exists "pets own" on public.pets;
create policy "pets own" on public.pets for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
