CREATE TABLE ${gold_db}.campaign_daily_kpi
WITH (
  format = 'PARQUET',
  external_location = 's3://${s3_bucket}/${gold_prefix}/campaign_daily_kpi/'
) AS
WITH preorder_base AS (
  SELECT
    TRY_CAST(campaign_id AS BIGINT) AS campaign_id,
    dt, title, category_name, biz_model, status_simplified, remaining_day,
    achievement_rate, funding_ratio, target_amount, total_funding_amount,
    participation_cnt, signature_cnt, snapshot_ts
  FROM ${silver_db}.preorder
  WHERE TRY_CAST(campaign_id AS BIGINT) IS NOT NULL
),
daily_base AS (
  SELECT *
  FROM (
    SELECT *, row_number() OVER (PARTITION BY campaign_id, dt ORDER BY snapshot_ts DESC) AS rn
    FROM preorder_base
  )
  WHERE rn = 1
),
daily_with_prev AS (
  SELECT
    campaign_id, dt, title, category_name, biz_model, status_simplified,
    remaining_day,
    CASE WHEN remaining_day < 0 THEN 'ended' WHEN remaining_day = 0 THEN 'D-day' ELSE CONCAT('D-', CAST(remaining_day AS VARCHAR)) END AS remaining_day_label,
    achievement_rate, funding_ratio, target_amount, total_funding_amount, participation_cnt, signature_cnt, snapshot_ts,
    LAG(total_funding_amount) OVER (PARTITION BY campaign_id ORDER BY dt) AS prev_total_funding_amount,
    LAG(participation_cnt) OVER (PARTITION BY campaign_id ORDER BY dt) AS prev_participation_cnt,
    LAG(signature_cnt) OVER (PARTITION BY campaign_id ORDER BY dt) AS prev_signature_cnt,
    LAG(achievement_rate) OVER (PARTITION BY campaign_id ORDER BY dt) AS prev_achievement_rate
  FROM daily_base
)
SELECT
  campaign_id, dt, title, category_name, biz_model, status_simplified,
  remaining_day, remaining_day_label, achievement_rate, funding_ratio, target_amount,
  total_funding_amount, participation_cnt, signature_cnt,
  prev_total_funding_amount, prev_participation_cnt, prev_signature_cnt, prev_achievement_rate,
  total_funding_amount - prev_total_funding_amount AS funding_amount_dod,
  CASE WHEN prev_total_funding_amount IS NULL OR prev_total_funding_amount = 0 THEN NULL ELSE CAST(total_funding_amount - prev_total_funding_amount AS DOUBLE) / prev_total_funding_amount END AS funding_amount_dod_rate,
  participation_cnt - prev_participation_cnt AS participation_dod,
  CASE WHEN prev_participation_cnt IS NULL OR prev_participation_cnt = 0 THEN NULL ELSE CAST(participation_cnt - prev_participation_cnt AS DOUBLE) / prev_participation_cnt END AS participation_dod_rate,
  signature_cnt - prev_signature_cnt AS signature_dod,
  CASE WHEN prev_signature_cnt IS NULL OR prev_signature_cnt = 0 THEN NULL ELSE CAST(signature_cnt - prev_signature_cnt AS DOUBLE) / prev_signature_cnt END AS signature_dod_rate,
  achievement_rate - prev_achievement_rate AS achievement_rate_dod,
  snapshot_ts
FROM daily_with_prev
