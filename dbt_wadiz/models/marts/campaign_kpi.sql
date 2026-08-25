-- 캠페인 단위 핵심 KPI 허브 테이블. Silver 4종을 캠페인 기준으로 집계.
with preorder_base as (
  select
    try_cast(campaign_id as bigint) as campaign_id,
    maker_id, maker_name, corp_name, title, category_code, category_name, core_message,
    open_ts, close_ts, snapshot_dt, snapshot_ts,
    remaining_day, remaining_days_at_snapshot,
    achievement_rate, funding_ratio, target_amount, total_funding_amount,
    participation_cnt, signature_cnt, status_simplified, biz_model,
    is_adult, has_coupon, maker_club_grade,
    is_delivery_available, is_global_shipping_available, thumbnail_url, dt
  from {{ source('wadiz_silver', 'preorder') }}
  where try_cast(campaign_id as bigint) is not null
),
preorder_latest as (
  select *
  from (
    select *, row_number() over (partition by campaign_id order by snapshot_ts desc, dt desc) as rn
    from preorder_base
  )
  where rn = 1
),
supporter_agg as (
  select
    try_cast(campaign_id as bigint) as campaign_id,
    count(distinct user_id_hash) as supporter_user_cnt,
    count(distinct case when is_purchaser = true then user_id_hash end) as purchaser_cnt,
    count(distinct case when is_signer = true then user_id_hash end) as signer_user_cnt,
    sum(case when is_purchaser = true then coalesce(backing_amount, 0) else 0 end) as supporter_backing_amount,
    avg(case when is_purchaser = true then cast(backing_amount as double) end) as avg_supporter_backing_amount
  from {{ source('wadiz_silver', 'supporter') }}
  where try_cast(campaign_id as bigint) is not null
  group by try_cast(campaign_id as bigint)
),
wish_agg as (
  select try_cast(campaign_id as bigint) as campaign_id, count(distinct user_id_hash) as wish_user_cnt
  from {{ source('wadiz_silver', 'wishes') }}
  where try_cast(campaign_id as bigint) is not null
  group by try_cast(campaign_id as bigint)
),
comment_agg as (
  select
    try_cast(campaign_id as bigint) as campaign_id,
    count(distinct comment_id) as comment_cnt,
    sum(case when contains_question_mark = true or strpos(coalesce(keyword_groups, ''), 'question') > 0 then 1 else 0 end) as question_cnt,
    sum(case when is_maker = true or is_owner = true then 1 else 0 end) as answer_cnt,
    avg(cast(sentiment_score as double)) as avg_sentiment_score,
    sum(case when sentiment_label = 'positive' then 1 else 0 end) as positive_comment_cnt,
    sum(case when sentiment_label = 'negative' then 1 else 0 end) as negative_comment_cnt,
    sum(case when sentiment_label = 'neutral' then 1 else 0 end) as neutral_comment_cnt
  from {{ source('wadiz_silver', 'comments') }}
  where try_cast(campaign_id as bigint) is not null
  group by try_cast(campaign_id as bigint)
)
select
  p.campaign_id,
  p.title, p.category_name, p.category_code, p.biz_model, p.status_simplified,
  p.maker_id, p.maker_name, p.corp_name, p.core_message, p.maker_club_grade,
  p.has_coupon, p.is_delivery_available, p.is_global_shipping_available,
  p.open_ts, p.close_ts, p.snapshot_dt, p.snapshot_ts,
  p.remaining_day,
  case when p.remaining_day < 0 then 'ended' when p.remaining_day = 0 then 'D-day' else concat('D-', cast(p.remaining_day as varchar)) end as remaining_day_label,
  p.achievement_rate, p.funding_ratio, p.target_amount, p.total_funding_amount,
  p.participation_cnt, p.signature_cnt,
  coalesce(s.supporter_user_cnt, 0) as supporter_user_cnt,
  coalesce(s.purchaser_cnt, 0) as purchaser_cnt,
  coalesce(s.signer_user_cnt, 0) as signer_user_cnt,
  coalesce(s.supporter_backing_amount, 0) as supporter_backing_amount,
  s.avg_supporter_backing_amount,
  case when coalesce(s.purchaser_cnt, 0) = 0 then null else cast(s.supporter_backing_amount as double) / s.purchaser_cnt end as arppu,
  coalesce(w.wish_user_cnt, 0) as wish_user_cnt,
  coalesce(c.comment_cnt, 0) as comment_cnt,
  coalesce(c.question_cnt, 0) as question_cnt,
  coalesce(c.answer_cnt, 0) as answer_cnt,
  c.avg_sentiment_score,
  coalesce(c.positive_comment_cnt, 0) as positive_comment_cnt,
  coalesce(c.negative_comment_cnt, 0) as negative_comment_cnt,
  coalesce(c.neutral_comment_cnt, 0) as neutral_comment_cnt,
  coalesce(p.signature_cnt, 0) + coalesce(w.wish_user_cnt, 0) + coalesce(c.comment_cnt, 0) as reaction_cnt,
  p.dt
from preorder_latest p
left join supporter_agg s on p.campaign_id = s.campaign_id
left join wish_agg w on p.campaign_id = w.campaign_id
left join comment_agg c on p.campaign_id = c.campaign_id
