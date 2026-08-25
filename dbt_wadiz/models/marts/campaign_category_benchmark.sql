-- 동일 카테고리 평균 대비 성과 비교. campaign_kpi(허브)를 카테고리로 집계 후 결합.
with base as (
  select * from {{ ref('campaign_kpi') }} where category_name is not null
),
category_stats as (
  select
    category_name,
    count(distinct campaign_id) as category_campaign_cnt,
    avg(cast(total_funding_amount as double)) as category_avg_funding_amount,
    approx_percentile(cast(total_funding_amount as double), 0.5) as category_median_funding_amount,
    avg(cast(achievement_rate as double)) as category_avg_achievement_rate,
    avg(cast(participation_cnt as double)) as category_avg_participation_cnt,
    avg(cast(signature_cnt as double)) as category_avg_signature_cnt,
    avg(cast(wish_user_cnt as double)) as category_avg_wish_user_cnt,
    avg(cast(comment_cnt as double)) as category_avg_comment_cnt
  from base
  group by category_name
)
select
  b.campaign_id, b.dt, b.title, b.category_name,
  b.total_funding_amount as selected_total_funding_amount,
  b.achievement_rate as selected_achievement_rate,
  b.participation_cnt as selected_participation_cnt,
  b.signature_cnt as selected_signature_cnt,
  b.wish_user_cnt as selected_wish_user_cnt,
  b.comment_cnt as selected_comment_cnt,
  s.category_campaign_cnt,
  s.category_avg_funding_amount,
  s.category_median_funding_amount,
  s.category_avg_achievement_rate,
  s.category_avg_participation_cnt,
  s.category_avg_signature_cnt,
  s.category_avg_wish_user_cnt,
  s.category_avg_comment_cnt,
  case when s.category_avg_funding_amount = 0 then null else cast(b.total_funding_amount as double) / s.category_avg_funding_amount end as selected_vs_category_avg_funding_ratio,
  case when s.category_avg_achievement_rate = 0 then null else cast(b.achievement_rate as double) / s.category_avg_achievement_rate end as selected_vs_category_avg_achievement_ratio,
  case when s.category_avg_participation_cnt = 0 then null else cast(b.participation_cnt as double) / s.category_avg_participation_cnt end as selected_vs_category_avg_participation_ratio
from base b
left join category_stats s on b.category_name = s.category_name
