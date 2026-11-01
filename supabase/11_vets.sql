-- にくきゅうレーダー 追加設定（第11弾）：動物病院を場所の種類に追加

alter table public.spot_reviews drop constraint if exists spot_reviews_spot_type_check;
alter table public.spot_reviews add constraint spot_reviews_spot_type_check check (spot_type in ('dogpark','cafe','vet',''));
alter table public.user_spots drop constraint if exists user_spots_spot_type_check;
alter table public.user_spots add constraint user_spots_spot_type_check check (spot_type in ('dogpark','cafe','vet'));
