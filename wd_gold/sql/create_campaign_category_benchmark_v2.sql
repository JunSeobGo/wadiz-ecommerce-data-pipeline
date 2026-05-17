CREATE TABLE ${gold_db}.campaign_category_benchmark
WITH (
  format = 'PARQUET',
  external_location = 's3://${s3_bucket}/${gold_prefix}/campaign_category_benchmark/'
) AS
WITH base AS (
  SELECT * FROM ${gold_db}.campaign_kpi WHERE category_name IS NOT NULL
),
category_stats AS (
  SELECT
    category_name,
    COUNT(DISTINCT campaign_id) AS category_campaign_cnt,
    AVG(CAST(total_funding_amount AS DOUBLE)) AS category_avg_funding_amount,
    approx_percentile(CAST(total_funding_amount AS DOUBLE), 0.5) AS category_median_funding_amount,
    AVG(CAST(achievement_rate AS DOUBLE)) AS category_avg_achievement_rate,
    AVG(CAST(participation_cnt AS DOUBLE)) AS category_avg_participation_cnt,
    AVG(CAST(signature_cnt AS DOUBLE)) AS category_avg_signature_cnt,
    AVG(CAST(wish_user_cnt AS DOUBLE)) AS category_avg_wish_user_cnt,
    AVG(CAST(comment_cnt AS DOUBLE)) AS category_avg_comment_cnt
  FROM base
  GROUP BY category_name
)
SELECT
  b.campaign_id, b.dt, b.title, b.category_name,
  b.total_funding_amount AS selected_total_funding_amount,
  b.achievement_rate AS selected_achievement_rate,
  b.participation_cnt AS selected_participation_cnt,
  b.signature_cnt AS selected_signature_cnt,
  b.wish_user_cnt AS selected_wish_user_cnt,
  b.comment_cnt AS selected_comment_cnt,
  s.category_campaign_cnt,
  s.category_avg_funding_amount,
  s.category_median_funding_amount,
  s.category_avg_achievement_rate,
  s.category_avg_participation_cnt,
  s.category_avg_signature_cnt,
  s.category_avg_wish_user_cnt,
  s.category_avg_comment_cnt,
  CASE WHEN s.category_avg_funding_amount = 0 THEN NULL ELSE CAST(b.total_funding_amount AS DOUBLE) / s.category_avg_funding_amount END AS selected_vs_category_avg_funding_ratio,
  CASE WHEN s.category_avg_achievement_rate = 0 THEN NULL ELSE CAST(b.achievement_rate AS DOUBLE) / s.category_avg_achievement_rate END AS selected_vs_category_avg_achievement_ratio,
  CASE WHEN s.category_avg_participation_cnt = 0 THEN NULL ELSE CAST(b.participation_cnt AS DOUBLE) / s.category_avg_participation_cnt END AS selected_vs_category_avg_participation_ratio
FROM base b
LEFT JOIN category_stats s ON b.category_name = s.category_name
