# Silver Layer Design

Silver Layer는 Bronze raw JSON을 Gold에서 안정적으로 사용할 수 있는 분석 엔티티 테이블로 정제하는 구간이다.

## Table Grain

| Table | Grain | 설명 |
|---|---|---|
| preorder | campaign_id x snapshot_ts | 캠페인 성과 스냅샷 |
| comments | comment_id | 댓글, 문의, 답변 |
| supporter | campaign_id x user_id_hash x participated_at | 구매자, 지지서명 |
| fundings | user_id_hash x campaign_id x funded_at | 펀딩 이력 |
| wishes | user_id_hash x campaign_id x snapshot_dt | 찜 스냅샷 |
| user_info | user_id_hash x snapshot_dt | 유저 프로필 스냅샷 |
| detail | campaign_id x dt | 캠페인 상세 수집 결과 |

## Null 처리 원칙

- 식별자 key는 임의로 채우지 않는다. null이면 error row로 분리한다.
- 금액/카운트는 분석상 0이 타당한 경우만 0으로 채운다.
- timestamp는 임의값으로 채우지 않는다.
- 텍스트는 분석 편의를 위해 empty string으로 치환할 수 있다.
- 수집 실패와 원래 없음은 `is_error`, `crawl_status`, `error_type`으로 구분한다.

## Idempotency

같은 `dt` 재실행 시:

1. Bronze read
2. transform
3. validate
4. 기존 Silver partition 삭제
5. 정상 row Parquet write
6. error row Parquet write

## Error Row Path

```text
s3://wd-data-lake/silver_error/wadiz/{{table}}/dt=YYYYMMDD/
```
