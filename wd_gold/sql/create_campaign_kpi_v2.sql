CREATE TABLE ${gold_db}.campaign_kpi
WITH (
  format = 'PARQUET',
  external_location = 's3://${s3_bucket}/${gold_prefix}/campaign_kpi/'
) AS
WITH preorder_base AS (
  SELECT
    TRY_CAST(campaign_id AS BIGINT) AS campaign_id,
    maker_id, maker_name, corp_name, title, category_code, category_name, core_message,
    open_ts, close_ts, snapshot_dt, snapshot_ts,
    remaining_day, remaining_days_at_snapshot,
    achievement_rate, funding_ratio, target_amount, total_funding_amount,
    participation_cnt, signature_cnt, status_simplified, biz_model,
    is_adult, has_coupon, maker_club_grade,
    is_delivery_available, is_global_shipping_available, thumbnail_url, dt
  FROM ${silver_db}.preorder
  WHERE TRY_CAST(campaign_id AS BIGINT) IS NOT NULL
),
preorder_latest AS (
  SELECT *
  FROM (
    SELECT *, row_number() OVER (PARTITION BY campaign_id ORDER BY snapshot_ts DESC, dt DESC) AS rn
    FROM preorder_base
  )
  WHERE rn = 1
),
supporter_agg AS (
  SELECT
    TRY_CAST(campaign_id AS BIGINT) AS campaign_id,
    COUNT(DISTINCT user_id_hash) AS supporter_user_cnt,
    COUNT(DISTINCT CASE WHEN is_purchaser = true THEN user_id_hash END) AS purchaser_cnt,
    COUNT(DISTINCT CASE WHEN is_signer = true THEN user_id_hash END) AS signer_user_cnt,
    SUM(CASE WHEN is_purchaser = true THEN COALESCE(backing_amount, 0) ELSE 0 END) AS supporter_backing_amount,
    AVG(CASE WHEN is_purchaser = true THEN CAST(backing_amount AS DOUBLE) END) AS avg_supporter_backing_amount
  FROM ${silver_db}.supporter
  WHERE TRY_CAST(campaign_id AS BIGINT) IS NOT NULL
  GROUP BY TRY_CAST(campaign_id AS BIGINT)
),
wish_agg AS (
  SELECT TRY_CAST(campaign_id AS BIGINT) AS campaign_id, COUNT(DISTINCT user_id_hash) AS wish_user_cnt
  FROM ${silver_db}.wishes
  WHERE TRY_CAST(campaign_id AS BIGINT) IS NOT NULL
  GROUP BY TRY_CAST(campaign_id AS BIGINT)
),
comment_agg AS (
  SELECT
    TRY_CAST(campaign_id AS BIGINT) AS campaign_id,
    COUNT(DISTINCT comment_id) AS comment_cnt,
    SUM(CASE WHEN contains_question_mark = true OR strpos(COALESCE(keyword_groups, ''), 'question') > 0 THEN 1 ELSE 0 END) AS question_cnt,
    SUM(CASE WHEN is_maker = true OR is_owner = true THEN 1 ELSE 0 END) AS answer_cnt,
    AVG(CAST(sentiment_score AS DOUBLE)) AS avg_sentiment_score,
    SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) AS positive_comment_cnt,
    SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) AS negative_comment_cnt,
    SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) AS neutral_comment_cnt
  FROM ${silver_db}.comments
  WHERE TRY_CAST(campaign_id AS BIGINT) IS NOT NULL
  GROUP BY TRY_CAST(campaign_id AS BIGINT)
)
SELECT
  p.campaign_id,
  p.title, p.category_name, p.category_code, p.biz_model, p.status_simplified,
  p.maker_id, p.maker_name, p.corp_name, p.core_message, p.maker_club_grade,
  p.has_coupon, p.is_delivery_available, p.is_global_shipping_available,
  p.open_ts, p.close_ts, p.snapshot_dt, p.snapshot_ts,
  p.remaining_day,
  CASE WHEN p.remaining_day < 0 THEN 'ended' WHEN p.remaining_day = 0 THEN 'D-day' ELSE CONCAT('D-', CAST(p.remaining_day AS VARCHAR)) END AS remaining_day_label,
  p.achievement_rate, p.funding_ratio, p.target_amount, p.total_funding_amount,
  p.participation_cnt, p.signature_cnt,
  COALESCE(s.supporter_user_cnt, 0) AS supporter_user_cnt,
  COALESCE(s.purchaser_cnt, 0) AS purchaser_cnt,
  COALESCE(s.signer_user_cnt, 0) AS signer_user_cnt,
  COALESCE(s.supporter_backing_amount, 0) AS supporter_backing_amount,
  s.avg_supporter_backing_amount,
  CASE WHEN COALESCE(s.purchaser_cnt, 0) = 0 THEN NULL ELSE CAST(s.supporter_backing_amount AS DOUBLE) / s.purchaser_cnt END AS arppu,
  COALESCE(w.wish_user_cnt, 0) AS wish_user_cnt,
  COALESCE(c.comment_cnt, 0) AS comment_cnt,
  COALESCE(c.question_cnt, 0) AS question_cnt,
  COALESCE(c.answer_cnt, 0) AS answer_cnt,
  c.avg_sentiment_score,
  COALESCE(c.positive_comment_cnt, 0) AS positive_comment_cnt,
  COALESCE(c.negative_comment_cnt, 0) AS negative_comment_cnt,
  COALESCE(c.neutral_comment_cnt, 0) AS neutral_comment_cnt,
  COALESCE(p.signature_cnt, 0) + COALESCE(w.wish_user_cnt, 0) + COALESCE(c.comment_cnt, 0) AS reaction_cnt,
  p.dt
FROM preorder_latest p
LEFT JOIN supporter_agg s ON p.campaign_id = s.campaign_id
LEFT JOIN wish_agg w ON p.campaign_id = w.campaign_id
LEFT JOIN comment_agg c ON p.campaign_id = c.campaign_id
