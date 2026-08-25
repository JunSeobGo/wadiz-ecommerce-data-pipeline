-- 대시보드/Export 공개용 뷰. maker_id 등 내부 식별자 제외한 컬럼만 노출.
select
  campaign_id, title, category_name, category_code, biz_model, status_simplified,
  maker_name, corp_name, core_message, maker_club_grade, has_coupon,
  is_delivery_available, is_global_shipping_available, open_ts, close_ts,
  snapshot_dt, snapshot_ts, remaining_day, remaining_day_label, achievement_rate,
  funding_ratio, target_amount, total_funding_amount, participation_cnt, signature_cnt,
  supporter_user_cnt, purchaser_cnt, signer_user_cnt, supporter_backing_amount,
  avg_supporter_backing_amount, arppu, wish_user_cnt, comment_cnt, question_cnt,
  answer_cnt, avg_sentiment_score, positive_comment_cnt, negative_comment_cnt,
  neutral_comment_cnt, reaction_cnt, dt
from {{ ref('campaign_kpi') }}
