# Wadiz E-commerce Data Pipeline

크라우드펀딩/프리오더 데이터를 Bronze, Silver, Gold 계층으로 처리하고, 판매자용 Streamlit 대시보드와 플랫폼 운영용 Tableau 연계 구조까지 설계한 데이터 엔지니어링 포트폴리오 프로젝트입니다.

이 저장소는 GitHub 공개용 데모 버전입니다. 실제 API 도메인, AWS 계정 ID, 인증키, 개인 경로, 원천 데이터는 제거하거나 마스킹했습니다.

## 1. 프로젝트 목표

운영자가 특정 메이커와 캠페인을 선택했을 때 아래 내용을 한 화면에서 확인할 수 있도록 데이터 파이프라인과 대시보드를 구성했습니다.

- 캠페인 핵심 KPI
- 누적 펀딩금액, 달성률, 참여자 수, 지지서명 수
- 전일 대비 펀딩 증감
- 댓글 감성 및 키워드 반응
- 관심 행동에서 참여로 이어지는 전환 흐름
- 동일 카테고리 대비 성과 비교
- 운영 체크포인트

## 2. 전체 아키텍처

```text
Source API / Web
↓
Airflow on EC2
↓
ECS Fargate Bronze Crawlers
↓
S3 Bronze Raw JSON
↓
ECS Fargate Silver ETL
↓
S3 Silver Parquet
↓
Athena Silver Tables
↓
dbt-athena on ECS Fargate (Gold Modeling + Test)
↓
S3 / Athena Gold
↓
Streamlit Seller Dashboard

Athena Gold Public View
↓
Google Sheets Export
↓
Tableau Platform Dashboard
```

## 3. 공개용 데모에서 바꾼 점

- 실제 API 도메인을 `SOURCE_BASE_URL`, `SOURCE_PREORDER_SEARCH_URL` 환경변수로 분리했습니다.
- 공개 기본값은 `https://example.invalid`로 설정했습니다.
- 실제 AWS account id, subnet id, security group id, role arn은 모두 placeholder로 교체했습니다.
- `.env`, `.venv`, `__pycache__`, 인증 파일, pem key는 제외했습니다.
- Streamlit은 `dashboard/streamlit_seller_demo/data`의 fake CSV 데이터를 읽는 데모 모드로 구성했습니다.

## 4. 폴더 구조

```text
airflow/dags/                         Airflow DAG. Bronze, Silver, Gold, Export로 분리
airflow/include/wadiz_airflow/         Airflow 공통 실행 유틸
wd_bronze/                             Bronze Raw JSON 수집 코드
wd_silver/                             Silver Parquet 정제 코드
dbt_wadiz/                             Gold 모델링 dbt 프로젝트 (dbt-athena, source/ref/test)
wd_gold/sql/                           (구) Athena Gold CTAS SQL. dbt 이전 전 버전 참고용
wd_dashboard_export/                   Gold public view → Google Sheets export
dashboard/streamlit_seller_demo/       fake CSV 기반 판매자용 Streamlit 데모 대시보드(실제로는 S3 -> Streamlit)
infra/terraform/                       기존 EC2 기반 IaC 시작 코드
docs/                                  설계 및 GitHub 업로드 체크리스트
scripts/                               실행/검증 스크립트
```

## 5. Airflow DAG 분리 기준

기존의 단일 daily DAG는 실패 지점 파악이 어려워서 Medallion 계층별로 분리했습니다.

| DAG | 트리거 | 역할 |
|---|---|---|
| `wadiz_01_bronze_daily_dag` | 매일 02:00 (cron) | 원천 응답을 Bronze Raw JSON으로 저장 |
| `wadiz_02_silver_daily_dag` | Bronze 완료 시 (Dataset) | JSON flatten, 타입 정리, 중복 제거, PII 처리 |
| `wadiz_03_gold_daily_dag` | Silver 완료 시 (Dataset) | dbt-athena(ECS)로 Gold Mart 생성 + 데이터 테스트 |
| `wadiz_04_tableau_export_dag` | Gold 완료 시 (Dataset) | Gold public view를 Google Sheets로 export |

Bronze만 시각(02:00)으로 시작하고, 이후 단계는 Airflow Dataset(데이터 인지 스케줄링)으로 연결했습니다. 상위 단계가 실제로 완료됐을 때만 하위 단계가 실행되므로, 시간차 스케줄에서 발생하던 "상위 실패에도 하위가 빈/과거 데이터로 실행되는" 문제를 구조적으로 제거했습니다. 처리 기준일(dt)은 Dataset 이벤트 extra로 전달해 전 단계가 동일한 날짜를 처리합니다.

## 6. Streamlit 데모 실행

```bash
cd dashboard/streamlit_seller_demo
pip install -r requirements.txt
streamlit run app.py --server.port 8503
```

Windows PowerShell에서는 아래 스크립트를 사용할 수 있습니다.

```powershell
.\scripts
un_seller_demo_dashboard.ps1
```

## 7. Terraform IaC 실행 방식

Terraform 예시는 기존 Airflow EC2가 살아있다는 가정에서 작성했습니다. 처음에는 기존 리소스를 조회만 하도록 구성했습니다.

```powershell
cd infra/terraform/ec2_airflow_existing/dev
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
```

처음 목표는 아래 결과입니다.

```text
Plan: 0 to add, 0 to change, 0 to destroy
```

그 후 `enable_managed_log_group`, `enable_ecr_lifecycle_policy`를 true로 바꾸면서 낮은 위험도 리소스부터 Terraform 관리 대상으로 확장합니다.

## 8. GitHub 업로드 전 검증

```bash
python scripts/scan_sensitive_strings.py
python -m compileall airflow wd_bronze wd_silver wd_dashboard_export scripts
```

## 9. 운영 보완점

현재 데모 버전은 포트폴리오 설명과 구조 검증을 위한 공개용 패키지입니다. 실제 운영 수준으로 확장하려면 아래 항목을 추가합니다.

- failed campaign/user 재처리 큐
- schema validation 강화
- row count, null rate, duplicate rate 검증
- CloudWatch 또는 Slack 알림
- GitHub Actions OIDC 기반 AWS 배포
- Streamlit 운영 배포 환경 분리
- Terraform remote backend와 state locking 구성
