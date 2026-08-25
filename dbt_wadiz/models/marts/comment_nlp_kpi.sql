-- 댓글 키워드 그룹별 감성 KPI. keyword_groups를 행으로 펼쳐 집계.
with comment_base as (
  select try_cast(campaign_id as bigint) as campaign_id, dt, comment_id, sentiment_label, sentiment_score, keyword_groups
  from {{ source('wadiz_silver', 'comments') }}
  where try_cast(campaign_id as bigint) is not null
),
exploded as (
  select c.campaign_id, c.dt, c.comment_id, c.sentiment_label, c.sentiment_score, trim(keyword_group) as keyword_group
  from comment_base c
  cross join unnest(split(coalesce(nullif(c.keyword_groups, ''), 'general'), ',')) as t(keyword_group)
),
agg as (
  select
    campaign_id, dt, keyword_group,
    count(distinct comment_id) as comment_cnt,
    sum(case when sentiment_label = 'positive' then 1 else 0 end) as positive_comment_cnt,
    sum(case when sentiment_label = 'neutral' then 1 else 0 end) as neutral_comment_cnt,
    sum(case when sentiment_label = 'negative' then 1 else 0 end) as negative_comment_cnt,
    avg(cast(sentiment_score as double)) as avg_sentiment_score
  from exploded
  group by campaign_id, dt, keyword_group
)
select
  campaign_id, dt, keyword_group, comment_cnt, positive_comment_cnt, neutral_comment_cnt, negative_comment_cnt,
  case when comment_cnt = 0 then null else cast(positive_comment_cnt as double) / comment_cnt end as positive_rate,
  case when comment_cnt = 0 then null else cast(negative_comment_cnt as double) / comment_cnt end as negative_rate,
  avg_sentiment_score,
  keyword_group as keyword_group_label,
  comment_cnt as keyword_count,
  negative_comment_cnt as negative_keyword_count
from agg
