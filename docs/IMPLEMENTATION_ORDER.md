# Implementation Order

1. `.env.example`을 `.env`로 복사하고 VPC 값을 수정한다.
2. `ecs_task_definitions/wd_silver_etl_task_definition.json`을 등록한다.
3. `wd-silver-etl`을 dry-run으로 실행한다.
4. dry-run 성공 후 실제 write 테스트를 수행한다.
5. Airflow EC2에 DAG와 include 모듈을 배포한다.
6. `wadiz_campaign_snapshot_dag`에서 preorder Silver task만 먼저 테스트한다.
7. `wadiz_comments_nlp_dag`를 연결한다.
8. Gold CTAS를 연결한다.
9. Tableau export를 연결한다.
