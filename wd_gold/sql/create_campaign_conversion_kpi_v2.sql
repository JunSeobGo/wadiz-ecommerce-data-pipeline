CREATE TABLE ${gold_db}.campaign_conversion_kpi
WITH (
  format = 'PARQUET',
  external_location = 's3://${s3_bucket}/${gold_prefix}/campaign_conversion_kpi/'
) AS
WITH funding_agg AS (
  SELECT
    TRY_CAST(campaign_id AS BIGINT) AS campaign_id,
    COUNT(DISTINCT user_id_hash) AS funding_user_cnt,
    SUM(COALESCE(amount, 0)) AS user_history_funding_amount
  FROM ${silver_db}.fundings
  WHERE TRY_CAST(campaign_id AS BIGINT) IS NOT NULL
  GROUP BY TRY_CAST(campaign_id AS BIGINT)
)
SELECT
  b.campaign_id, b.dt, b.title, b.category_name, b.biz_model, b.status_simplified,
  b.wish_user_cnt, b.signature_cnt, b.participation_cnt, b.purchaser_cnt,
  COALESCE(f.funding_user_cnt, 0) AS funding_user_cnt,
  CASE WHEN COALESCE(b.wish_user_cnt, 0) = 0 THEN NULL ELSE CAST(b.purchaser_cnt AS DOUBLE) / b.wish_user_cnt END AS wish_to_purchase_rate,
  CASE WHEN COALESCE(b.signature_cnt, 0) = 0 THEN NULL ELSE CAST(b.purchaser_cnt AS DOUBLE) / b.signature_cnt END AS signature_to_purchase_rate,
  CASE WHEN COALESCE(b.wish_user_cnt, 0) = 0 THEN NULL ELSE CAST(b.participation_cnt AS DOUBLE) / b.wish_user_cnt END AS wish_to_participation_rate,
  b.arppu, b.total_funding_amount, b.achievement_rate,
  COALESCE(f.user_history_funding_amount, 0) AS user_history_funding_amount
FROM ${gold_db}.campaign_kpi b
LEFT JOIN funding_agg f ON b.campaign_id = f.campaign_id
