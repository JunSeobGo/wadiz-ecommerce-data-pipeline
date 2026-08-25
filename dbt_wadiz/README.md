# wadiz_gold (dbt-athena)

Gold 모델링 계층을 담당하는 dbt 프로젝트입니다. Silver 이후의 SQL Modeling 책임을 Airflow에서 분리했습니다.

## 역할 분리

- **Silver (ECS/Pandas)**: flatten, 타입 정리, PII 해싱, 중복 제거
- **Gold (dbt/SQL)**: Silver를 `source`로 참조해 KPI Mart 생성 + 데이터 테스트
- **Airflow**: "언제 실행할지"만 관리. 모델 간 의존성/실행 순서는 dbt가 `ref`로 판단

## 구조

```
models/
├── staging/_sources.yml     Silver 테이블 6종을 source로 선언
├── marts/                   Gold Mart 6종 (materialized: table)
│   ├── campaign_kpi.sql          (허브: preorder/supporter/wishes/comments 집계)
│   ├── campaign_daily_kpi.sql
│   ├── campaign_conversion_kpi.sql   ← ref(campaign_kpi)
│   ├── campaign_category_benchmark.sql ← ref(campaign_kpi)
│   ├── comment_nlp_kpi.sql
│   ├── campaign_response_performance.sql
│   └── _marts.yml            not_null / unique 데이터 테스트
└── public/                  대시보드/Export용 공개 뷰 6종 (materialized: view)
```

`campaign_conversion_kpi`, `campaign_category_benchmark`는 `{{ ref('campaign_kpi') }}`로 의존성을 선언하므로 dbt가 실행 순서를 자동으로 결정합니다.

## 실행

```bash
cp profiles.yml.example profiles.yml   # 또는 환경변수(WADIZ_*, DBT_ATHENA_*) 주입
dbt deps        # (패키지 사용 시)
dbt build       # = dbt run + dbt test (모델 생성 후 테스트 통과까지)
```

운영에서는 Airflow가 ECS Fargate로 이 프로젝트 컨테이너를 실행해 `dbt build`를 수행합니다(`wadiz_03_gold_daily_dag`).

## 확장 방향

현재는 전체 snapshot(`materialized: table`)으로 기존 CTAS 동작을 그대로 이전했습니다. Athena scan량/실행시간이 커지면 `campaign_daily_kpi`부터 `incremental` + `partitioned_by=['dt']` + `insert_overwrite`로 전환할 수 있습니다(dbt-athena 지원).
