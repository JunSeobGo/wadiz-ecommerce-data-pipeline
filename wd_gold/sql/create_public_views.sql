CREATE OR REPLACE VIEW ${gold_db}.campaign_kpi_public AS
SELECT
  campaign_id, title, category_name, category_code, biz_model, status_simplified,
  maker_name, corp_name, core_message, maker_club_grade, has_coupon,
  is_delivery_available, is_global_shipping_available, open_ts, close_ts,
  snapshot_dt, snapshot_ts, remaining_day, remaining_day_label, achievement_rate,
  funding_ratio, target_amount, total_funding_amount, participation_cnt, signature_cnt,
  supporter_user_cnt, purchaser_cnt, signer_user_cnt, supporter_backing_amount,
  avg_supporter_backing_amount, arppu, wish_user_cnt, comment_cnt, question_cnt,
  answer_cnt, avg_sentiment_score, positive_comment_cnt, negative_comment_cnt,
  neutral_comment_cnt, reaction_cnt, dt
FROM ${gold_db}.campaign_kpi;

CREATE OR REPLACE VIEW ${gold_db}.campaign_daily_kpi_public AS
SELECT * FROM ${gold_db}.campaign_daily_kpi;

CREATE OR REPLACE VIEW ${gold_db}.campaign_conversion_kpi_public AS
SELECT * FROM ${gold_db}.campaign_conversion_kpi;

CREATE OR REPLACE VIEW ${gold_db}.comment_nlp_kpi_public AS
SELECT * FROM ${gold_db}.comment_nlp_kpi;

CREATE OR REPLACE VIEW ${gold_db}.campaign_response_performance_public AS
SELECT * FROM ${gold_db}.campaign_response_performance;

CREATE OR REPLACE VIEW ${gold_db}.campaign_category_benchmark_public AS
SELECT * FROM ${gold_db}.campaign_category_benchmark;
