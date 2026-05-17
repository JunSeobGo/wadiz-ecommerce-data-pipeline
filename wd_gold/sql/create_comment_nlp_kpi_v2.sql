CREATE TABLE ${gold_db}.comment_nlp_kpi
WITH (
  format = 'PARQUET',
  external_location = 's3://${s3_bucket}/${gold_prefix}/comment_nlp_kpi/'
) AS
WITH comment_base AS (
  SELECT TRY_CAST(campaign_id AS BIGINT) AS campaign_id, dt, comment_id, sentiment_label, sentiment_score, keyword_groups
  FROM ${silver_db}.comments
  WHERE TRY_CAST(campaign_id AS BIGINT) IS NOT NULL
),
exploded AS (
  SELECT c.campaign_id, c.dt, c.comment_id, c.sentiment_label, c.sentiment_score, TRIM(keyword_group) AS keyword_group
  FROM comment_base c
  CROSS JOIN UNNEST(SPLIT(COALESCE(NULLIF(c.keyword_groups, ''), 'general'), ',')) AS t(keyword_group)
),
agg AS (
  SELECT
    campaign_id, dt, keyword_group,
    COUNT(DISTINCT comment_id) AS comment_cnt,
    SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) AS positive_comment_cnt,
    SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) AS neutral_comment_cnt,
    SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative_comment_cnt,
    AVG(CAST(sentiment_score AS DOUBLE)) AS avg_sentiment_score
  FROM exploded
  GROUP BY campaign_id, dt, keyword_group
)
SELECT
  campaign_id, dt, keyword_group, comment_cnt, positive_comment_cnt, neutral_comment_cnt, negative_comment_cnt,
  CASE WHEN comment_cnt = 0 THEN NULL ELSE CAST(positive_comment_cnt AS DOUBLE) / comment_cnt END AS positive_rate,
  CASE WHEN comment_cnt = 0 THEN NULL ELSE CAST(negative_comment_cnt AS DOUBLE) / comment_cnt END AS negative_rate,
  avg_sentiment_score,
  keyword_group AS keyword_group_label,
  comment_cnt AS keyword_count,
  negative_comment_cnt AS negative_keyword_count
FROM agg
