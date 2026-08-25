-- 메이커 응답 성과(질문 대비 답변율). Silver comments 기반.
with comment_base as (
  select
    try_cast(campaign_id as bigint) as campaign_id,
    dt, comment_id, contains_question_mark, keyword_groups, is_answered, is_maker, is_owner, time_to_first_answer_min
  from {{ source('wadiz_silver', 'comments') }}
  where try_cast(campaign_id as bigint) is not null
),
agg as (
  select
    campaign_id, dt,
    count(distinct comment_id) as comment_cnt,
    sum(case when contains_question_mark = true or strpos(coalesce(keyword_groups, ''), 'question') > 0 then 1 else 0 end) as question_cnt,
    sum(case when is_answered = true then 1 else 0 end) as answered_question_cnt,
    sum(case when is_maker = true or is_owner = true then 1 else 0 end) as maker_answer_cnt,
    avg(time_to_first_answer_min) as avg_time_to_first_answer_min
  from comment_base
  group by campaign_id, dt
)
select
  campaign_id, dt, comment_cnt, question_cnt, answered_question_cnt, maker_answer_cnt, avg_time_to_first_answer_min,
  case when question_cnt = 0 then null else cast(answered_question_cnt as double) / question_cnt end as answer_rate
from agg
