-- 비즈니스 규칙: 구매자는 서포터의 부분집합이므로 purchaser_cnt는 supporter_user_cnt를 넘을 수 없다.
-- 위반 행이 있으면(0행이 아니면) 테스트 실패.
select
  campaign_id,
  supporter_user_cnt,
  purchaser_cnt
from {{ ref('campaign_kpi') }}
where purchaser_cnt > supporter_user_cnt
