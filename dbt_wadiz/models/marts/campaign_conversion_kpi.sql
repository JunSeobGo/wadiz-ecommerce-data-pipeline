-- 관심→참여→구매 전환 KPI. campaign_kpi(허브) + fundings 집계 결합.
with funding_agg as (
  select
    try_cast(campaign_id as bigint) as campaign_id,
    count(distinct user_id_hash) as funding_user_cnt,
    sum(coalesce(amount, 0)) as user_history_funding_amount
  from {{ source('wadiz_silver', 'fundings') }}
  where try_cast(campaign_id as bigint) is not null
  group by try_cast(campaign_id as bigint)
)
select
  b.campaign_id, b.dt, b.title, b.category_name, b.biz_model, b.status_simplified,
  b.wish_user_cnt, b.signature_cnt, b.participation_cnt, b.purchaser_cnt,
  coalesce(f.funding_user_cnt, 0) as funding_user_cnt,
  case when coalesce(b.wish_user_cnt, 0) = 0 then null else cast(b.purchaser_cnt as double) / b.wish_user_cnt end as wish_to_purchase_rate,
  case when coalesce(b.signature_cnt, 0) = 0 then null else cast(b.purchaser_cnt as double) / b.signature_cnt end as signature_to_purchase_rate,
  case when coalesce(b.wish_user_cnt, 0) = 0 then null else cast(b.participation_cnt as double) / b.wish_user_cnt end as wish_to_participation_rate,
  b.arppu, b.total_funding_amount, b.achievement_rate,
  coalesce(f.user_history_funding_amount, 0) as user_history_funding_amount
from {{ ref('campaign_kpi') }} b
left join funding_agg f on b.campaign_id = f.campaign_id
