-- 비즈니스 규칙: 같은 키워드 그룹에서 긍정+부정 비율의 합은 1을 넘을 수 없다
-- (긍정/부정/중립이 상호배타이므로). 부동소수 오차 허용치를 둔다.
select
  campaign_id,
  keyword_group,
  positive_rate,
  negative_rate
from {{ ref('comment_nlp_kpi') }}
where coalesce(positive_rate, 0) + coalesce(negative_rate, 0) > 1.0000001
