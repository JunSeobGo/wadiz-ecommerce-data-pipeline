CREATE TABLE ${gold_db}.campaign_response_performance
WITH (
  format = 'PARQUET',
  external_location = 's3://${s3_bucket}/${gold_prefix}/campaign_response_performance/'
) AS
WITH comment_base AS (
  SELECT
    TRY_CAST(campaign_id AS BIGINT) AS campaign_id,
    dt, comment_id, contains_question_mark, keyword_groups, is_answered, is_maker, is_owner, time_to_first_answer_min
  FROM ${silver_db}.comments
  WHERE TRY_CAST(campaign_id AS BIGINT) IS NOT NULL
),
agg AS (
  SELECT
    campaign_id, dt,
    COUNT(DISTINCT comment_id) AS comment_cnt,
    SUM(CASE WHEN contains_question_mark = true OR strpos(COALESCE(keyword_groups, ''), 'question') > 0 THEN 1 ELSE 0 END) AS question_cnt,
    SUM(CASE WHEN is_answered = true THEN 1 ELSE 0 END) AS answered_question_cnt,
    SUM(CASE WHEN is_maker = true OR is_owner = true THEN 1 ELSE 0 END) AS maker_answer_cnt,
    AVG(time_to_first_answer_min) AS avg_time_to_first_answer_min
  FROM comment_base
  GROUP BY campaign_id, dt
)
SELECT
  campaign_id, dt, comment_cnt, question_cnt, answered_question_cnt, maker_answer_cnt, avg_time_to_first_answer_min,
  CASE WHEN question_cnt = 0 THEN NULL ELSE CAST(answered_question_cnt AS DOUBLE) / question_cnt END AS answer_rate
FROM agg
