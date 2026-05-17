# Validation Checklist

## ECS

- Task Definition role ARN이 프로젝트 role과 일치하는가
- ECS task stoppedReason이 정상인가
- Container exitCode가 0인가
- CloudWatch log group이 생성되었는가

## Silver

- Bronze input row count가 로그에 남는가
- Silver output row count가 로그에 남는가
- duplicate 제거 전/후 count가 로그에 남는가
- required key null row가 error row로 분리되는가
- dt partition이 YYYYMMDD인가
- 동일 dt 재실행 시 기존 partition이 삭제되는가

## Gold

- QuickSight workgroup이 아닌 workgroup에서 CTAS를 실행하는가
- Gold table name과 S3 path가 모두 `_v2` 기준으로 일치하는가
- CTAS 실행 전 S3 path를 삭제하는가

## Tableau Public

- public view에 user_id_hash가 없는가
- public view에 댓글 원문이 없는가
- public view에 개별 구매/찜 row가 없는가
