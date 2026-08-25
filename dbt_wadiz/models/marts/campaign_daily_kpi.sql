-- 캠페인 일자별 KPI + 전일 대비(DoD) 증감. Silver preorder 스냅샷 기반.
with preorder_base as (
  select
    try_cast(campaign_id as bigint) as campaign_id,
    dt, title, category_name, biz_model, status_simplified, remaining_day,
    achievement_rate, funding_ratio, target_amount, total_funding_amount,
    participation_cnt, signature_cnt, snapshot_ts
  from {{ source('wadiz_silver', 'preorder') }}
  where try_cast(campaign_id as bigint) is not null
),
daily_base as (
  select *
  from (
    select *, row_number() over (partition by campaign_id, dt order by snapshot_ts desc) as rn
    from preorder_base
  )
  where rn = 1
),
daily_with_prev as (
  select
    campaign_id, dt, title, category_name, biz_model, status_simplified,
    remaining_day,
    case when remaining_day < 0 then 'ended' when remaining_day = 0 then 'D-day' else concat('D-', cast(remaining_day as varchar)) end as remaining_day_label,
    achievement_rate, funding_ratio, target_amount, total_funding_amount, participation_cnt, signature_cnt, snapshot_ts,
    lag(total_funding_amount) over (partition by campaign_id order by dt) as prev_total_funding_amount,
    lag(participation_cnt) over (partition by campaign_id order by dt) as prev_participation_cnt,
    lag(signature_cnt) over (partition by campaign_id order by dt) as prev_signature_cnt,
    lag(achievement_rate) over (partition by campaign_id order by dt) as prev_achievement_rate
  from daily_base
)
select
  campaign_id, dt, title, category_name, biz_model, status_simplified,
  remaining_day, remaining_day_label, achievement_rate, funding_ratio, target_amount,
  total_funding_amount, participation_cnt, signature_cnt,
  prev_total_funding_amount, prev_participation_cnt, prev_signature_cnt, prev_achievement_rate,
  total_funding_amount - prev_total_funding_amount as funding_amount_dod,
  case when prev_total_funding_amount is null or prev_total_funding_amount = 0 then null else cast(total_funding_amount - prev_total_funding_amount as double) / prev_total_funding_amount end as funding_amount_dod_rate,
  participation_cnt - prev_participation_cnt as participation_dod,
  case when prev_participation_cnt is null or prev_participation_cnt = 0 then null else cast(participation_cnt - prev_participation_cnt as double) / prev_participation_cnt end as participation_dod_rate,
  signature_cnt - prev_signature_cnt as signature_dod,
  case when prev_signature_cnt is null or prev_signature_cnt = 0 then null else cast(signature_cnt - prev_signature_cnt as double) / prev_signature_cnt end as signature_dod_rate,
  achievement_rate - prev_achievement_rate as achievement_rate_dod,
  snapshot_ts
from daily_with_prev
